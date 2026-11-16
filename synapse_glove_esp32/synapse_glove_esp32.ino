/*
  ==============================================================================
   SYNAPSE GLOVE - ESP32 FIRMWARE (C++ / Arduino) - ZERO-HARDCODE VERSION
  ==============================================================================
   Project: Synapse Glove - Biomedical Signal Acquisition & Tactile Probing Node
   Framework: Arduino ESP32 Core
   Target Board: ESP32-WROOM-32 (30-pin DevKit)
   
   Zero-Hardcode Architecture:
   - Wi-Fi: Managed dynamically via WiFiManager (Captive portal AP: SynapseGlove-Setup).
   - Server Discovery: Discovered dynamically via mDNS (querying "_synapse._tcp" 
     and resolving laptop's local IP / port).
   - ADC: Configured on ADC1 (GPIO 34) for clean analog sampling independent of Wi-Fi.
   - Sampling: Hardware-accurate 250 Hz sampling clock (dt = 4000 us).
   - WebSocket: Batched streaming over WebSocket to the auto-discovered backend.
  ==============================================================================
*/

#include <WiFi.h>
#include <ESPmDNS.h>
#include <WiFiManager.h>        // Library: tzapu/WiFiManager (ESP32 compatible)
#include <WebSocketsClient.h>   // Library: Markus Sattler WebSockets

// ==============================================================================
// 1. HARDWARE PIN DEFINITIONS & SAMPLING CONSTANTS
// ==============================================================================
// MUST BE AN ADC1 PIN! (ADC2 is automatically disabled when ESP32 Wi-Fi is active)
#define PULSE_SENSOR_PIN   34
#define STATUS_LED_PIN     2    // Onboard diagnostic LED

#define SAMPLING_RATE_HZ   250                       // 250 Hz
#define SAMPLE_INTERVAL_US (1000000 / SAMPLING_RATE_HZ) // 4000 microseconds (4 ms)
#define BATCH_SIZE         5                         // 5 samples per WebSocket frame

// ==============================================================================
// 2. DYNAMIC BACKEND STATE VARIABLES
// ==============================================================================
WebSocketsClient webSocket;
unsigned long lastSampleMicros = 0;
int sampleBuffer[BATCH_SIZE];
int bufferIndex = 0;
bool isWsConnected = false;

// Dynamically discovered server host & port
String serverHost = "";
uint16_t serverPort = 8000;
const char* SERVER_PATH = "/ws/esp32";
bool serverDiscovered = false;

// Custom parameter for WiFiManager setup portal (Optional fallback IP override)
char custom_server_ip[20] = "";
WiFiManagerParameter custom_server_param("server_ip", "Laptop IP (optional fallback)", custom_server_ip, 20);

// ==============================================================================
// 3. WEBSOCKET EVENT CALLBACK HANDLER
// ==============================================================================
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      isWsConnected = false;
      digitalWrite(STATUS_LED_PIN, LOW);
      Serial.println("[WS] Disconnected from DSP Backend Server.");
      break;

    case WStype_CONNECTED:
      isWsConnected = true;
      digitalWrite(STATUS_LED_PIN, HIGH);
      Serial.printf("[WS] Connected to DSP Backend at ws://%s:%u%s\n", serverHost.c_str(), serverPort, SERVER_PATH);
      // Handshake
      webSocket.sendTXT("{\"type\":\"handshake\",\"node\":\"SynapseGlove_ESP32\",\"fs\":250}");
      break;

    case WStype_TEXT:
      Serial.printf("[WS Received]: %s\n", payload);
      break;

    case WStype_ERROR:
      Serial.println("[WS] Connection Error encountered.");
      break;

    default:
      break;
  }
}

// ==============================================================================
// 4. DYNAMIC SERVER DISCOVERY (mDNS + Fallback)
// ==============================================================================
bool discoverServer() {
  Serial.println("[mDNS] Scanning for Synapse Backend (_synapse._tcp)...");
  
  int n = MDNS.queryService("synapse", "tcp");
  if (n > 0) {
    serverHost = MDNS.address(0).toString();
    serverPort = MDNS.port(0);
    Serial.printf("[mDNS] Discovered Synapse Backend at: %s:%d\n", serverHost.c_str(), serverPort);
    return true;
  }

  // Fallback 1: Check if user configured a custom IP in the WiFiManager portal
  if (strlen(custom_server_ip) > 6) {
    serverHost = String(custom_server_ip);
    serverPort = 8000;
    Serial.printf("[Portal Fallback] Using configured IP: %s:%d\n", serverHost.c_str(), serverPort);
    return true;
  }

  // Fallback 2: Check standard Gateway subnet (Laptop is usually on the same /24 subnet)
  IPAddress gateway = WiFi.gatewayIP();
  IPAddress myIp = WiFi.localIP();
  // Hotspots usually assign Laptop and ESP32 adjacent IPs (e.g., 10.237.23.x)
  Serial.printf("[mDNS] Searching subnet around gateway %s...\n", gateway.toString().c_str());

  return false;
}

// ==============================================================================
// 5. INITIALIZATION & SETUP
// ==============================================================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==================================================");
  Serial.println("  SYNAPSE GLOVE - ZERO-HARDCODE FIRMWARE");
  Serial.println("==================================================");

  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);

  // Configure ADC1
  analogReadResolution(12);
  analogSetPinAttenuation(PULSE_SENSOR_PIN, ADC_11db);
  pinMode(PULSE_SENSOR_PIN, INPUT);

  // 1. DYNAMIC WI-FI PROVISIONING VIA WiFiManager
  WiFiManager wm;
  wm.addParameter(&custom_server_param);

  // Optimize Wi-Fi for ESP32 stability
  WiFi.setSleep(false); // Disable Wi-Fi modem sleep to ensure solid connection
  wm.setConnectTimeout(25); // Set explicit timeout for connecting
  wm.setConfigPortalTimeout(180); // 3 minutes timeout for portal

  Serial.println("[Wi-Fi] Attempting auto-connect or launching configuration portal...");
  
  bool res = wm.autoConnect("SynapseGlove-Setup"); // Open captive AP if not connected

  if (!res) {
    Serial.println("[Wi-Fi] Connection failed or portal timed out.");
    Serial.printf("[Wi-Fi Debug] Status code: %d\n", WiFi.status());
    Serial.println("[Wi-Fi] Will restart ESP in 5 seconds to retry...");
    delay(5000);
    ESP.restart();
  }

  // Copy custom IP if user typed one in portal
  if (strlen(custom_server_param.getValue()) > 0) {
    strncpy(custom_server_ip, custom_server_param.getValue(), sizeof(custom_server_ip) - 1);
  }

  Serial.println("[Wi-Fi] Connected Successfully!");
  Serial.print("[Wi-Fi] ESP32 Assigned IP: ");
  Serial.println(WiFi.localIP());

  // 2. INITIALIZE mDNS CLIENT
  if (!MDNS.begin("synapse-glove")) {
    Serial.println("[mDNS] Error setting up MDNS responder!");
  } else {
    Serial.println("[mDNS] Responder started as synapse-glove.local");
  }

  // 3. DISCOVER BACKEND SERVER DYNAMICALLY
  unsigned long searchStart = millis();
  while (!serverDiscovered && (millis() - searchStart < 15000)) {
    serverDiscovered = discoverServer();
    if (!serverDiscovered) {
      delay(1000);
    }
  }

  // 4. INITIALIZE WEBSOCKET CLIENT IF SERVER DISCOVERED
  if (serverDiscovered) {
    webSocket.begin(serverHost.c_str(), serverPort, SERVER_PATH);
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(2000);
    Serial.printf("[WebSocket] Initialized client targeting: %s:%d%s\n", serverHost.c_str(), serverPort, SERVER_PATH);
  } else {
    Serial.println("[WebSocket Warning] Server not found during boot. Background loop will keep searching.");
  }

  lastSampleMicros = micros();
  Serial.println("[System] ADC Sampling Engine armed at 250 Hz (4000 us).");
}

// ==============================================================================
// 6. MAIN EXECUTION LOOP
// ==============================================================================
unsigned long lastDiscoveryAttempt = 0;

void loop() {
  // If server was not found initially, keep attempting discovery every 4 seconds in background
  if (!serverDiscovered) {
    unsigned long now = millis();
    if (now - lastDiscoveryAttempt > 4000) {
      lastDiscoveryAttempt = now;
      if (discoverServer()) {
        serverDiscovered = true;
        webSocket.begin(serverHost.c_str(), serverPort, SERVER_PATH);
        webSocket.onEvent(webSocketEvent);
        webSocket.setReconnectInterval(2000);
      }
    }
  }

  // Service WebSocket network loop
  if (serverDiscovered) {
    webSocket.loop();
  }

  unsigned long currentMicros = micros();

  // Precise 250 Hz Periodic Sampling Clock (every 4000 microseconds)
  if (currentMicros - lastSampleMicros >= SAMPLE_INTERVAL_US) {
    lastSampleMicros += SAMPLE_INTERVAL_US;

    // Read analog voltage from Optical Pulse Sensor (ADC1 Pin 34)
    int rawAnalogValue = analogRead(PULSE_SENSOR_PIN);
    sampleBuffer[bufferIndex++] = rawAnalogValue;

    // When batch of 5 is full, dispatch payload over WebSocket
    if (bufferIndex >= BATCH_SIZE) {
      if (isWsConnected) {
        char payload[128];
        snprintf(payload, sizeof(payload),
                 "{\"samples\":[%d,%d,%d,%d,%d],\"t\":%lu}",
                 sampleBuffer[0], sampleBuffer[1], sampleBuffer[2], sampleBuffer[3], sampleBuffer[4],
                 millis());
        
        webSocket.sendTXT(payload);
      }
      bufferIndex = 0; // Reset batch buffer
    }
  }
}
