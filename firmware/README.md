# VeriPath Hardware Firmware

## Devices
- VP-LIV Collar — ESP32 + DS18B20 + RGB LED
- VP-LIV Rumen Bolus — ESP32 + waterproof DS18B20 + deep sleep

## Arduino Libraries Required
Install via Arduino IDE Library Manager:
- ArduinoJson by Benoit Blanchon (v6+)
- DallasTemperature by Miles Burton
- OneWire by Paul Stoffregen
- Board: esp32 by Espressif (v2+)

## Setup Per Device
1. Copy config.h — fill in WiFi + Supabase credentials
2. Set ANIMAL_TAG to the VP-LIV-XXXX tag from Animal Registry
3. Set SPECIES to Goat, Cattle, or Sheep
4. Flash collar_firmware.ino or bolus_firmware.ino
5. Monitor Serial at 115200 baud to verify first reading

## Wiring — Collar (ESP32)
Component       ESP32 Pin
DS18B20 DATA    GPIO 4
DS18B20 VCC     3.3V
DS18B20 GND     GND
4.7k resistor   DATA to VCC
LED RED         GPIO 25
LED YELLOW      GPIO 26
LED GREEN       GPIO 27

## Wiring — Bolus (ESP32 minimal)
Component             ESP32 Pin
DS18B20 DATA sealed   GPIO 4
DS18B20 VCC           3.3V
DS18B20 GND           GND
4.7k resistor         DATA to VCC

## Data Flow
ESP32 reads DS18B20
  -> classifies GREEN/YELLOW/RED per species thresholds
  -> POSTs to Supabase animal_temps table
  -> PATCHes animals table health_status
  -> VeriPath app reads updated status
  -> RED triggers WhatsApp alert to owner + vet

## Reading Intervals
- Collar: every 5 minutes (stays on)
- Bolus: every 15 minutes (deep sleep between reads)

## Supabase RLS Policies
Run in Supabase SQL editor:

CREATE POLICY device_insert_temps ON animal_temps
FOR INSERT WITH CHECK (true);

CREATE POLICY device_update_animals ON animals
FOR UPDATE USING (true);
