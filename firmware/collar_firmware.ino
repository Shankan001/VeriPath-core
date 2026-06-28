/*
 * VeriPath Africa — VP-LIV Collar Firmware
 * ESP32 + DS18B20 temperature sensor
 * Reads temp every 5 min → POST to Supabase animal_temps
 * LED: GREEN (normal) / YELLOW (mild) / RED (alert)
 *
 * Wiring:
 *   DS18B20 DATA → GPIO 4
 *   LED RED      → GPIO 25
 *   LED YELLOW   → GPIO 26
 *   LED GREEN    → GPIO 27
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <time.h>
#include "config.h"

// ── Pin definitions ────────────────────────────────────────────────────
#define ONE_WIRE_BUS  4
#define LED_RED       25
#define LED_YELLOW    26
#define LED_GREEN     27

OneWire           oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// ── Species thresholds ─────────────────────────────────────────────────
struct Thresholds {
    float normal_min;
    float normal_max;
    float mild;
    float significant;
    float emergency;
};

Thresholds getThresholds() {
    String sp = String(SPECIES);
    if (sp == "Cattle") return {38.0, 39.3, 39.5, 39.8, 40.5};
    if (sp == "Sheep")  return {38.5, 39.5, 39.8, 40.0, 41.0};
    return {38.5, 40.0, 40.2, 40.5, 41.5};  // Goat default
}

// ── Classify temperature ───────────────────────────────────────────────
String classifyTemp(float temp) {
    Thresholds t = getThresholds();
    int hour = 0;
    struct tm timeinfo;
    if (getLocalTime(&timeinfo)) hour = timeinfo.tm_hour;
    bool isDaytime = (hour >= 6 && hour < 18);

    if (temp < t.normal_min)   return "BLUE";
    if (temp <= t.normal_max)  return "GREEN";
    if (temp < t.significant) {
        return isDaytime ? "YELLOW" : "RED";
    }
    return "RED";
}

// ── Set LED ────────────────────────────────────────────────────────────
void setLED(String status) {
    digitalWrite(LED_RED,    LOW);
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_GREEN,  LOW);

    if (status == "GREEN")  digitalWrite(LED_GREEN,  HIGH);
    if (status == "YELLOW") digitalWrite(LED_YELLOW, HIGH);
    if (status == "RED")    digitalWrite(LED_RED,    HIGH);
    if (status == "BLUE")   {
        // Hypothermia — flash blue via red+green alternating
        for (int i = 0; i < 3; i++) {
            digitalWrite(LED_GREEN, HIGH); delay(200);
            digitalWrite(LED_GREEN, LOW);
            digitalWrite(LED_RED,   HIGH); delay(200);
            digitalWrite(LED_RED,   LOW);
        }
    }
}

// ── Time of day string ─────────────────────────────────────────────────
String getTimeOfDay() {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) return "unknown";
    int h = timeinfo.tm_hour;
    if (h >= 6  && h < 12) return "morning";
    if (h >= 12 && h < 17) return "afternoon";
    if (h >= 17 && h < 20) return "evening";
    return "night";
}

// ── ISO timestamp ──────────────────────────────────────────────────────
String getISO8601() {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) return "1970-01-01T00:00:00Z";
    char buf[30];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    return String(buf);
}

// ── POST to Supabase ───────────────────────────────────────────────────
bool postToSupabase(float temp, String status) {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi disconnected — skipping POST");
        return false;
    }

    HTTPClient http;
    String url = String(SUPABASE_URL) + "/rest/v1/animal_temps";
    http.begin(url);
    http.addHeader("Content-Type",  "application/json");
    http.addHeader("apikey",        SUPABASE_ANON_KEY);
    http.addHeader("Authorization", String("Bearer ") + SUPABASE_ANON_KEY);
    http.addHeader("Prefer",        "return=minimal");

    // Build JSON payload
    StaticJsonDocument<256> doc;
    doc["animal_tag"]    = ANIMAL_TAG;
    doc["company"]       = COMPANY;
    doc["recorded_by"]   = RECORDED_BY;
    doc["temp_celsius"]  = round(temp * 10.0) / 10.0;
    doc["recorded_at"]   = getISO8601();
    doc["time_of_day"]   = getTimeOfDay();
    doc["health_status"] = status;
    doc["notes"]         = "auto:collar";

    String payload;
    serializeJson(doc, payload);
    Serial.println("POST → " + payload);

    int code = http.POST(payload);
    Serial.println("Response: " + String(code));
    http.end();
    return (code == 201 || code == 200);
}

// ── Also update animals table health_status ────────────────────────────
bool updateAnimalStatus(String status) {
    if (WiFi.status() != WL_CONNECTED) return false;

    HTTPClient http;
    String url = String(SUPABASE_URL)
               + "/rest/v1/animals?animal_tag=eq."
               + String(ANIMAL_TAG);
    http.begin(url);
    http.addHeader("Content-Type",  "application/json");
    http.addHeader("apikey",        SUPABASE_ANON_KEY);
    http.addHeader("Authorization", String("Bearer ") + SUPABASE_ANON_KEY);
    http.addHeader("Prefer",        "return=minimal");

    StaticJsonDocument<64> doc;
    doc["health_status"] = status;
    String payload;
    serializeJson(doc, payload);

    int code = http.PATCH(payload);
    http.end();
    return (code == 204 || code == 200);
}

// ── WiFi connect ───────────────────────────────────────────────────────
void connectWiFi() {
    Serial.print("Connecting to WiFi");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ WiFi connected: " + WiFi.localIP().toString());
        // Sync time (Nairobi = UTC+3)
        configTime(10800, 0, "pool.ntp.org", "time.nist.gov");
        Serial.println("⏰ Time synced");
    } else {
        Serial.println("\n❌ WiFi failed — will retry on next cycle");
    }
}

// ── Setup ──────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    sensors.begin();

    pinMode(LED_RED,    OUTPUT);
    pinMode(LED_YELLOW, OUTPUT);
    pinMode(LED_GREEN,  OUTPUT);

    // Startup flash — all LEDs
    digitalWrite(LED_RED,    HIGH);
    digitalWrite(LED_YELLOW, HIGH);
    digitalWrite(LED_GREEN,  HIGH);
    delay(1000);
    digitalWrite(LED_RED,    LOW);
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_GREEN,  LOW);

    Serial.println("\n🐄 VeriPath Collar — " + String(ANIMAL_TAG));
    Serial.println("Species: " + String(SPECIES));
    connectWiFi();
}

// ── Loop ───────────────────────────────────────────────────────────────
void loop() {
    // Reconnect WiFi if dropped
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("Reconnecting WiFi...");
        connectWiFi();
    }

    // Read temperature
    sensors.requestTemperatures();
    float temp = sensors.getTempCByIndex(0);

    if (temp == DEVICE_DISCONNECTED_C) {
        Serial.println("❌ Sensor error — no reading");
        // Flash all LEDs to signal error
        for (int i = 0; i < 5; i++) {
            digitalWrite(LED_RED, HIGH); delay(100);
            digitalWrite(LED_RED, LOW);  delay(100);
        }
        delay(TEMP_READ_INTERVAL_MS);
        return;
    }

    String status = classifyTemp(temp);
    Serial.println("🌡 Temp: " + String(temp) + "°C → " + status);

    // Set LED
    setLED(status);

    // Post to Supabase
    bool posted = postToSupabase(temp, status);
    if (posted) {
        updateAnimalStatus(status);
        Serial.println("✅ Reading posted");
    }

    // Wait for next reading
    delay(TEMP_READ_INTERVAL_MS);
}
