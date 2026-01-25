#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <Adafruit_DRV2605.h>

// --- HARDWARE CONFIG ---
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);
Adafruit_DRV2605 drv;

// --- RAIN VARIABLES ---
int targetIntensity = 0;      
float currentIntensity = 0;   

// --- TUNING KNOB: RAMP SPEED ---
// INCREASED to 4.0 for faster reaction time (0.5s to max)
float rampSpeed = 4.0; 

unsigned long nextDropTime = 0;
unsigned long lastRampTime = 0;

void setup() {
  Serial.begin(115200);

  // Display Init
  pinMode(TFT_BACKLITE, OUTPUT);
  digitalWrite(TFT_BACKLITE, HIGH);
  tft.init(135, 240);
  tft.setRotation(3);
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextColor(ST77XX_CYAN);
  tft.setTextSize(2);
  tft.println("Crisp Storm v2");

  if (!drv.begin()) {
    tft.setTextColor(ST77XX_RED);
    tft.println("Motor Error!");
    while (1);
  }
  
  drv.selectLibrary(1);
  drv.setMode(DRV2605_MODE_INTTRIG);
  drv.useERM(); 
}

void loop() {
  unsigned long currentMillis = millis();

  // 1. LISTEN
  if (Serial.available() > 0) {
    targetIntensity = Serial.read();
  }

  // 2. SMOOTHING (Run every 10ms)
  if (currentMillis - lastRampTime > 10) {
    lastRampTime = currentMillis;

    if (abs(currentIntensity - targetIntensity) > rampSpeed) {
      if (currentIntensity < targetIntensity) {
        currentIntensity += rampSpeed; 
      } else {
        currentIntensity -= rampSpeed;
      }
    } else {
      currentIntensity = targetIntensity;
    }
  }

  // 3. GENERATE RAIN
  if (currentIntensity > 20) { 
    
    if (currentMillis > nextDropTime) {
      triggerDroplet((int)currentIntensity);
      
      // --- TIMING LOGIC ---
      int minDelay, maxDelay;

      // We ensure the delays are never shorter than the effect duration!
      
      if (currentIntensity < 100) {
        // LIGHT RAIN: Slow, occasional
        minDelay = map((int)currentIntensity, 20, 100, 400, 150);
        maxDelay = map((int)currentIntensity, 20, 100, 1000, 400);
      } 
      else if (currentIntensity < 200) {
        // STEADY RAIN: Active
        minDelay = map((int)currentIntensity, 100, 200, 100, 50);
        maxDelay = map((int)currentIntensity, 100, 200, 300, 120);
      } 
      else {
        // STORM: Chaos
        // We cap the speed at 40ms. Going faster than this usually makes
        // the motor feel weaker because it floats between on/off.
        minDelay = 40;
        maxDelay = 90;
      }
      
      nextDropTime = currentMillis + random(minDelay, maxDelay);
    }
  }
}

void triggerDroplet(int intensity) {
  
  if (intensity > 220) {
    // TIER 3: STORM (Max Power)
    // Effect 1 is "Strong Click 100%" - The heaviest single hit available.
    drv.setWaveform(0, 1);  
  } 
  else if (intensity > 150) {
    // TIER 2: HEAVY RAIN
    // Effect 10 "Double Click 100%" is punchy but has texture.
    drv.setWaveform(0, 10);  
  } 
  else if (intensity > 50)
  {
    drv.setWaveform(0, 17); 
  }
  else {
    drv.setWaveform(0, 0);
  }
  
  drv.setWaveform(1, 0); 
  drv.go();
}