#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>

// Your WiFi credentials
const char* ssid = "Wifi Name";
const char* password = "WIFI Password";
// Server configuration - Use your computer's IP
const char* server = "computer's IP";// Changed to match settings.py
const int port = 8000;

// Sensor pins for 4 IR sensors
const int sensorPins[4] = {D0, D1, D2, D4};
const String sensorIds[4] = {"SENSOR_001", "SENSOR_002", "SENSOR_003", "SENSOR_004"};
bool lastStates[4] = {false, false, false, false};

// Status LED
const int statusLed = D3;

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println();
  Serial.println("🚗 Smart Parking System Starting...");
  Serial.println("📌 Sensor Pin Configuration:");
  Serial.println("   SENSOR_001 -> D0");
  Serial.println("   SENSOR_002 -> D1"); 
  Serial.println("   SENSOR_003 -> D2");
  Serial.println("   SENSOR_004 -> D4");
  Serial.println("   Status LED -> D3");
  
  // Initialize sensor pins
  for(int i = 0; i < 4; i++) {
    pinMode(sensorPins[i], INPUT_PULLUP);
    Serial.print("✅ Initialized Sensor ");
    Serial.print(sensorIds[i]);
    Serial.print(" on pin D");
    Serial.println(sensorPins[i]);
    
    // Read initial state
    lastStates[i] = digitalRead(sensorPins[i]) == LOW;
    Serial.print("   Initial State: ");
    Serial.println(lastStates[i] ? "OCCUPIED" : "VACANT");
  }
  
  // Initialize status LED
  pinMode(statusLed, OUTPUT);
  digitalWrite(statusLed, LOW);
  
  // Connect to WiFi
  connectToWiFi();
}

void connectToWiFi() {
  Serial.print("📡 Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    digitalWrite(statusLed, !digitalRead(statusLed));
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("✅ WiFi connected!");
    Serial.print("📱 IP Address: ");
    Serial.println(WiFi.localIP());
    digitalWrite(statusLed, HIGH);
    
    // Test server connection
    testServerConnection();
  } else {
    Serial.println();
    Serial.println("❌ WiFi connection failed!");
    digitalWrite(statusLed, LOW);
  }
}

void testServerConnection() {
  Serial.println("🔄 Testing server connection...");
  WiFiClient client;
  HTTPClient http;
  
  String testUrl = "http://" + String(server) + ":" + String(port) + "/api/test/";
  http.begin(client, testUrl);
  
  int httpCode = http.GET();
  if(httpCode == 200) {
    Serial.println("✅ Server connection successful!");
    
    // Send initial states to server
    sendInitialStates();
  } else {
    Serial.print("❌ Server connection failed. Code: ");
    Serial.println(httpCode);
  }
  http.end();
}

void sendInitialStates() {
  Serial.println("📡 Sending initial sensor states to server...");
  for(int i = 0; i < 4; i++) {
    bool currentState = digitalRead(sensorPins[i]) == LOW;
    sendSensorUpdate(sensorIds[i], currentState, i, true);
    delay(500);
  }
}

void loop() {
  // Maintain WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ WiFi disconnected! Reconnecting...");
    digitalWrite(statusLed, LOW);
    connectToWiFi();
    return;
  }
  
  // Monitor all sensors
  for(int i = 0; i < 4; i++) {
    bool currentState = digitalRead(sensorPins[i]) == LOW;
    
    if(currentState != lastStates[i]) {
      // State changed - send update to server
      sendSensorUpdate(sensorIds[i], currentState, i, false);
      lastStates[i] = currentState;
      
      // Visual feedback
      blinkLED();
    }
  }
  
  // Periodically print sensor status
  static unsigned long lastStatusTime = 0;
  if (millis() - lastStatusTime > 30000) { // Every 30 seconds
    Serial.println("\n📊 Current Sensor Status:");
    for(int i = 0; i < 4; i++) {
      Serial.print("  ");
      Serial.print(sensorIds[i]);
      Serial.print(" (D");
      Serial.print(sensorPins[i]);
      Serial.print("): ");
      Serial.println(lastStates[i] ? "OCCUPIED" : "VACANT");
    }
    lastStatusTime = millis();
  }
  
  delay(300); // Small delay for stability
}

void sendSensorUpdate(String sensorId, bool isOccupied, int sensorIndex, bool isInitial) {
  WiFiClient client;
  HTTPClient http;
  
  String url = "http://" + String(server) + ":" + String(port) + "/api/sensor-data/";
  
  if (!isInitial) {
    Serial.println();
    Serial.print("🔄 Sensor ");
    Serial.print(sensorId);
    Serial.print(" (Pin D");
    Serial.print(sensorPins[sensorIndex]);
    Serial.print(") changed to: ");
    Serial.println(isOccupied ? "🚗 OCCUPIED" : "🟢 VACANT");
  }
  
  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  StaticJsonDocument<200> doc;
  doc["sensor_id"] = sensorId;
  doc["is_occupied"] = isOccupied;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  if (!isInitial) {
    Serial.print("📦 Sending to server: ");
    Serial.println(jsonString);
  }
  
  int httpResponseCode = http.POST(jsonString);
  
  if(httpResponseCode > 0) {
    String response = http.getString();
    if (!isInitial) {
      Serial.print("✅ Server Response (");
      Serial.print(httpResponseCode);
      Serial.print("): ");
      Serial.println(response);
    }
  } else {
    Serial.print("❌ Error sending to server for ");
    Serial.print(sensorId);
    Serial.print(": ");
    Serial.println(httpResponseCode);
    
    // Blink rapidly on error
    for(int i = 0; i < 3; i++) {
      digitalWrite(statusLed, LOW);
      delay(150);
      digitalWrite(statusLed, HIGH);
      delay(150);
    }
  }
  
  http.end();
}

void blinkLED() {
  digitalWrite(statusLed, LOW);
  delay(80);
  digitalWrite(statusLed, HIGH);
}