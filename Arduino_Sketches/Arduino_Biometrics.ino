/*
  The "USB Streamer" for Arduino UNO Q
  - Reads Sensors (ADS1115)
  - Pipes data through the Linux Bridge to USB
*/
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <Arduino_RouterBridge.h> 

Adafruit_ADS1115 ads;

void setup() {
  // Use 'Monitor' instead of 'Serial' for USB communication
  Monitor.begin(115200); 

  // Initialize Sensors
  if (!ads.begin(0x48, &Wire1)) { 
    Monitor.println("Failed to init ADS1115.");
    while (1);
  }
  
  Monitor.println("Bio-Sensor Ready. Streaming JSON...");
}

void loop() {
  int16_t gsr_raw = ads.readADC_SingleEnded(0);   
  int16_t pulse_raw = ads.readADC_SingleEnded(1);

  // JSON Format
  String payload = "{\"gsr\":";
  payload += gsr_raw;
  payload += ",\"pulse\":";
  payload += pulse_raw;
  payload += "}";

  // Send to Laptop via USB
  Monitor.println(payload); 

  delay(50); // 20Hz
}