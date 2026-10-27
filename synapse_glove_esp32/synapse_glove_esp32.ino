/*
  ==============================================================================
   SYNAPSE GLOVE - ESP32 FIRMWARE (C++ / Arduino)
  ==============================================================================
   Project: Synapse Glove - Biomedical Signal Acquisition & Tactile Probing Node
   Framework: Arduino ESP32 Core
   Target Board: ESP32-WROOM-32 (30-pin DevKit)
   
   Functional Description:
   - Configures ADC1 (GPIO 34) for clean analog sampling independent of Wi-Fi.
   - Implements a hardware-accurate 250 Hz sampling clock (dt = 4000 microseconds).
   - Establishes a Wi-Fi connection and maintains a persistent WebSocket stream 
     to the Python FastAPI DSP backend.
   - Transmits batched sample payloads to minimize Wi-Fi frame overhead while
     maintaining near-zero (<20ms) telemetry latency.
  ==============================================================================
*/

#include <WiFi.h>
#include <WebSocketsClient.h> // Library: "WebSockets" by Markus Sattler (Install via Library Manager)

// ==============================================================================
// 1. NETWORK & BACKEND CONFIGURATION
// ==============================================================================
// Replace with your local Wi-Fi credentials
const char* WIFI_SSID     = "realme 11x 5G";
const char* WIFI_PASSWORD = "PHOENIX1";

// Replace with your Laptop / Host Machine's Local IP address (e.g., "192.168.1.100")
// Run 'ipconfig' (Windows) to find your IPv4 Address.
const char* SERVER_HOST   = "10.38.247.22";
const uint16_t SERVER_PORT = 8000;
const char* SERVER_PATH   = "/ws/esp32";

// ==============================================================================
// 2. HARDWARE PIN DEFINITIONS
// ==============================================================================
// MUST BE AN ADC1 PIN! (ADC2 is automatically disabled when ESP32 Wi-Fi is active)
// Supported ADC1 pins: 32, 33, 34, 35, 36 (VP), 39 (VN)
#define PULSE_SENSOR_PIN   34

// Onboard diagnostic LED (Optional, GPIO 2 on most ESP32 boards)
#define STATUS_LED_PIN     2

// ==============================================================================
// 3. SAMPLING & BATCHING CONSTANTS
// ==============================================================================
#define SAMPLING_RATE_HZ   250                       // Target: 250 Hz (Nyquist-compliant)
#define SAMPLE_INTERVAL_US (1000000 / SAMPLING_RATE_HZ) // 4000 microseconds (4 ms)

// Batch 5 samples per WebSocket frame (sends every 20ms = 50 packets/sec).
// This eliminates Wi-Fi congestion without introducing perceptual delay.
#define BATCH_SIZE         5

// ==============================================================================
// 4. GLOBAL STATE VARIABLES
// ==============================================================================
WebSocketsClient webSocket;
unsigned long lastSampleMicros = 0;
int sampleBuffer[BATCH_SIZE];
int bufferIndex = 0;
bool isWsConnected = false;

// ==============================================================================
// 5. WEBSOCKET EVENT CALLBACK HANDLER
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
      Serial.printf("[WS] Connected to DSP Backend at ws://%s:%u%s\n", SERVER_HOST, SERVER_PORT, SERVER_PATH);
      // Send handshake identification
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
// 6. INITIALIZATION & SETUP
// ==============================================================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==================================================");
  Serial.println("  SYNAPSE GLOVE - BIOMEDICAL ACQUISITION NODE");
  Serial.println("==================================================");

  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);

  // Configure ESP32 Analog-to-Digital Converter (ADC)
  // 12-bit resolution: 0 - 4095
  analogReadResolution(12);
  // Attenuation: 11dB allows measuring voltages up to ~3.3V
  analogSetPinAttenuation(PULSE_SENSOR_PIN, ADC_11db);
  pinMode(PULSE_SENSOR_PIN, INPUT);

  // 1. Connect to Wi-Fi
  Serial.printf("[Wi-Fi] Connecting to: %s\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN)); // Blink while connecting
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[Wi-Fi] Connected Successfully!");
    Serial.print("[Wi-Fi] ESP32 Assigned IP: ");
    Serial.println(WiFi.localIP());
    digitalWrite(STATUS_LED_PIN, HIGH);
  } else {
    Serial.println("\n[Wi-Fi] Failed to connect! Operating in standalone offline mode.");
  }

  // 2. Initialize WebSocket Client
  webSocket.begin(SERVER_HOST, SERVER_PORT, SERVER_PATH);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(2000); // Attempt auto-reconnect every 2 seconds

  lastSampleMicros = micros();
  Serial.println("[System] ADC Sampling Engine armed at 250 Hz (4000 us).");
}

// ==============================================================================
// 7. MAIN EXECUTION LOOP
// ==============================================================================
void loop() {
  // Service WebSocket protocol events (keep-alives, ping/pong)
  webSocket.loop();

  unsigned long currentMicros = micros();

  // Precise 250 Hz Periodic Sampling Clock
  if (currentMicros - lastSampleMicros >= SAMPLE_INTERVAL_US) {
    lastSampleMicros += SAMPLE_INTERVAL_US;

    // Read analog voltage from Optical Pulse Sensor (ADC1 Pin 34)
    int rawAnalogValue = analogRead(PULSE_SENSOR_PIN);
    sampleBuffer[bufferIndex++] = rawAnalogValue;

    // When batch is full, dispatch payload over WebSocket
    if (bufferIndex >= BATCH_SIZE) {
      if (isWsConnected) {
        // Construct compact JSON payload: {"samples":[v1,v2,v3,v4,v5],"t":12345}
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
