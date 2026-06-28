/*
 * VeriPath Africa — VP-LIV Rumen Bolus Firmware
 * ESP32 + DS18B20 (internal/waterproof probe)
 * Internal temperature — reads every 15 min
 * No LED (internal device) — status via Serial only
 *
 * Wiring:
 *   DS18B20 DATA → GPIO 4 (waterproof probe, ceramic-coated)
 *   Deep sleep between readings to save battery
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <esp_sleep.h>
#include <time.h>
#include "config.h"

#define ONE_WIRE_BUS 4
#define uS_TO_S_FACTOR 1000000ULL

OneWire           oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

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
    return {38.5, 40.0, 40.2, 40.5, 41.5};
}

String classifyTemp(float temp) {
    Thresholds t = getThresholds();
    struct tm timeinfo;
    int hour = 0;
    if (getLocalTime(&timeinfo)) hour = timeinfo.tm_hour;
    bool isDaytime = (hour >= 6 && hour < 18);
    if (temp < t.normal_min)  return "BLUE";
    if (temp <= t.normal_max) return "GREEN";
    if (temp < t.significant) return isDaytime ? "YELLOW" : "RED";
    return "RED";
}

String getTimeOfDay() {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) return "unknown";
    int h = timeinfo.tm_hour;
    if (h >= 6  && h < 12) return "morning";
    if (h >= 12 && h < 17) return "afternoon";
    if (h >= 17 && h < 20) return "evening";
    return "night";
}

String getISO8601() {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) return "1970-01-01T00:00:00Z";
    char buf[30];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    return String(buf);
}

void connectWiFi() {
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        configTime(10800, 0, "pool.ntp.org");
        delay(1000);
    }
}

bool postReading(float temp, String status) {
    if (WiFi.status() != WL_CONNECTED) return false;

    HTTPClient http;
    String url = String(SUPABASE_URL) + "/rest/v1/animal_temps";
    http.begin(url);
    http.addHeader("Content-Type",  "application/json");
    http.addHeader("apikey",        SUPABASE_ANON_KEY);
    http.addHeader("Authorization", String("Bearer ") + SUPABASE_ANON_KEY);
    http.addHeader("Prefer",        "return=minimal");

    StaticJsonDocument<256> doc;
    doc["animal_tag"]    = ANIMAL_TAG;
    doc["company"]       = COMPANY;
    doc["recorded_by"]   = RECORDED_BY;
    doc["temp_celsius"]  = round(temp * 10.0) / 10.0;
    doc["recorded_at"]   = getISO8601();
    doc["time_of_day"]   = getTimeOfDay();
    doc["health_status"] = status;
    doc["notes"]         = "auto:bolus";

    String payload;
    serializeJson(doc, payload);

    int code = http.POST(payload);
    http.end();

    // Update animal health_status
    if (code == 201 || code == 200) {
        HTTPClient http2;
        String url2 = String(SUPABASE_URL)
                    + "/rest/v1/animals?animal_tag=eq."
                    + String(ANIMAL_TAG);
        http2.begin(url2);
        http2.addHeader("Content-Type",  "application/json");
        http2.addHeader("apikey",        SUPABASE_ANON_KEY);
        http2.addHeader("Authorization", String("Bearer ") + SUPABASE_ANON_KEY);
        http2.addHeader("Prefer",        "return=minimal");
        StaticJsonDocument<64> doc2;
        doc2["health_status"] = status;
        String p2;
        serializeJson(doc2, p2);
        http2.PATCH(p2);
        http2.end();
        return true;
    }
    return false;
}

void setup() {
    Serial.begin(115200);
    Serial.println("\n💊 VeriPath Bolus — " + String(ANIMAL_TAG));

    sensors.begin();
    sensors.requestTemperatures();
    float temp = sensors.getTempCByIndex(0);

    if (temp == DEVICE_DISCONNECTED_C) {
        Serial.println("❌ Sensor error");
    } else {
        String status = classifyTemp(temp);
        Serial.println("🌡 Internal temp: " + String(temp) + "°C → " + status);
        connectWiFi();
        if (WiFi.status() == WL_CONNECTED) {
            bool ok = postReading(temp, status);
            Serial.println(ok ? "✅ Posted" : "❌ Post failed");
            WiFi.disconnect(true);
        }
    }

    // Deep sleep until next reading (saves battery)
    Serial.println("😴 Sleeping " +
        String(BOLUS_READ_INTERVAL_MS / 60000) + " minutes...");
    esp_sleep_enable_timer_wakeup(
        (uint64_t)(BOLUS_READ_INTERVAL_MS / 1000) * uS_TO_S_FACTOR
    );
    esp_deep_sleep_start();
}

void loop() {
    // Never reached — deep sleep restarts setup()
}
