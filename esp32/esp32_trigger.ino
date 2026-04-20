/*
  ClothingID — ESP32 trigger node
  ─────────────────────────────────────────────────────────
  Hardware:
    • Momentary push button between GPIO 4 and GND
    • Built-in LED on GPIO 2 (feedback blink)

  Flow:
    Button press → debounce → publish "scan" to TOPIC_TRIGGER via MQTT

  Libraries (Arduino Library Manager):
    • PubSubClient  by Nick O'Leary
    • WiFi           (built into ESP32 board package)

  Board: "ESP32 Dev Module" in Arduino IDE
*/

#include <WiFi.h>
#include <PubSubClient.h>

// ── CONFIG — edit these three ────────────────────────────
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASS     = "YOUR_WIFI_PASSWORD";
const char* MQTT_SERVER   = "10.23.198.21";   // server laptop LAN IP
// ─────────────────────────────────────────────────────────

const int   MQTT_PORT     = 1883;
const char* TOPIC_TRIGGER = "clothing/trigger";
const char* TOPIC_RESULT  = "clothing/result";   // optional: listen for result

const int   BTN_PIN       = 4;
const int   LED_PIN       = 2;

WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);

unsigned long lastPress   = 0;
const int     DEBOUNCE_MS = 300;
bool          lastState   = HIGH;


void blinkLED(int times, int ms = 100) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH); delay(ms);
    digitalWrite(LED_PIN, LOW);  delay(ms);
  }
}


void connectWiFi() {
  Serial.print("WiFi connecting");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nWiFi connected: " + WiFi.localIP().toString());
}


void mqttCallback(char* topic, byte* payload, unsigned int length) {
  // Optional: blink LED when result arrives from server
  if (String(topic) == TOPIC_RESULT) {
    Serial.print("Result received (");
    Serial.print(length);
    Serial.println(" bytes) — blink 3×");
    blinkLED(3, 150);
  }
}


void connectMQTT() {
  while (!mqtt.connected()) {
    Serial.print("MQTT connecting…");
    String clientId = "ESP32-ClothingID-" + String(random(0xffff), HEX);
    if (mqtt.connect(clientId.c_str())) {
      Serial.println(" connected");
      mqtt.subscribe(TOPIC_RESULT);
    } else {
      Serial.print(" failed rc="); Serial.println(mqtt.state());
      delay(3000);
    }
  }
}


void setup() {
  Serial.begin(115200);
  pinMode(BTN_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);

  connectWiFi();
  mqtt.setServer(MQTT_SERVER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  connectMQTT();

  blinkLED(2, 200);   // ready signal
  Serial.println("Ready. Press button to scan.");
}


void loop() {
  if (!mqtt.connected()) connectMQTT();
  mqtt.loop();

  bool state = digitalRead(BTN_PIN);

  // Falling edge (button pressed) with debounce
  if (state == LOW && lastState == HIGH) {
    unsigned long now = millis();
    if (now - lastPress > DEBOUNCE_MS) {
      lastPress = now;
      Serial.println("Button pressed → publishing trigger");
      digitalWrite(LED_PIN, HIGH);
      mqtt.publish(TOPIC_TRIGGER, "scan");
      delay(80);
      digitalWrite(LED_PIN, LOW);
    }
  }

  lastState = state;
  delay(10);
}
