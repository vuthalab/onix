#include "qCommand.h"
#include <math.h>
qCommand qC;

/*
Connections:
  * ADC1 - Vescent servo out (V_tune), -10 V to 10 V
  * ADC2 - Photodiode error
  * DAC1 - Laser piezo control. 0 to 10 V.
  * DAC2 - Same as DAC1.
  * Trigger - Triggers in the scan mode.

Modes:
  * Push mode: Keeps the ADC1 between 5 V to 7 V. When it crosses these limits, push on the piezo control to bring it back.
    Measures the ADC every ~1 ms.
  * Scan mode: Set DAC1 to sawtooth scan, centered at V_center and scan for +/- V_scan. When switching from the scan mode
    to the lock mode, the voltage should start at the V_center. When the voltage crosses V_center at the positive slope, trigger.
*/

// DAC parameters
float V_max = 10.0;
float V_min = 0.0;
float V_output = 0.0;

int state = 0;  // 0: Scan, 1: Push (normal), 2: Push (railed), 3: Push (dead).
const int SCAN_STATE = 0;
const int PUSH_NORMAL_STATE = 1;
const int PUSH_RAILED_STATE = 2;
const int PUSH_DEAD_STATE = 3;

// Scan parameters
float V_center = 5.0;
float V_scan = 0.0;
const int SCAN_STEPS = 10000;  // Separate the sawtooth scan as 10000 voltage steps.
const int SCAN_WAIT = 20; // Waits for 20 us with each step.

// Push parameters
float V_adc1_min = 5.0;
float V_adc1_max = 7.0;
float V_adc1_dead = 1.0;  // When the voltage is outside min and max by this value, stop the feedback.
float V_push_step = -1e-3;  // push step size. May be negative to reverse the gain direction.
uint16_t t_push = 1000;  // us

// Storing parameters
uint16_t t_error_sample = 2;  // us.
const int NUM_DATA = 50000;  // number of points to store.
float adc2_data[NUM_DATA];
int adc2_index = 0;
bool adc2_ready = false;
bool adc2_pause = false;

float adc1_value = 0.0;

float check_output_range(float value) {
  if (value > V_max) {
    value = V_max;
    if (state == PUSH_NORMAL_STATE) {
      state = PUSH_RAILED_STATE;
    }
  }
  else if (value < V_min) {
    value = V_min;
    if (state == PUSH_NORMAL_STATE) {
      state = PUSH_RAILED_STATE;
    }
  }
  return value;
}

void get_adc1(void) {
  adc1_value = (float)readADC1_from_ISR();
  if (state == SCAN_STATE) {
    return;
  }
  if (adc1_value < (V_adc1_min - V_adc1_dead)) {
    state = PUSH_DEAD_STATE;
  }
  else if (adc1_value < V_adc1_min) {
    V_output += V_push_step;
    state = PUSH_NORMAL_STATE;
  }
  else if (adc1_value > (V_adc1_max + V_adc1_dead)) {
    state = PUSH_DEAD_STATE;
  }
  else if (adc1_value > V_adc1_max) {
    V_output -= V_push_step;
    state = PUSH_NORMAL_STATE;
  }
  else {
    state = PUSH_NORMAL_STATE;
  }
  V_output = check_output_range(V_output);
  writeDAC(1, V_output);
  writeDAC(2, V_output);
}

void get_adc2(void) {
  if (!adc2_pause) {
    adc2_data[adc2_index] = readADC2_from_ISR(); 
    adc2_index++;
    if (adc2_index == NUM_DATA) {
      adc2_index = 0;
      adc2_ready = true;
    }
  }
  else {
    readADC2_from_ISR();
  }
}

void scan() {
  // starts from center, jumps to low, scans to high, and jumps back to center.
  float V_low = V_center - V_scan;
  float V_high = V_center + V_scan;
  float V_step = (V_high - V_low) / SCAN_STEPS;
  float V_scan_out = V_low - V_step;
  for (int i = 0; i < SCAN_STEPS + 1; i++) {
    V_scan_out += V_step;
    float actual_out = check_output_range(V_scan_out);
    writeDAC(1, actual_out);
    writeDAC(2, actual_out);
    if (i == (SCAN_STEPS / 2)) {
      triggerWrite(1, HIGH);
    }
    delayMicroseconds(SCAN_WAIT);
  }
  writeDAC(1, V_center);
  writeDAC(2, V_center);
  triggerWrite(1, LOW);
}

void cmd_state(qCommand& qC, Stream& S) {
  if (qC.next() != NULL) {
    int new_state = atoi(qC.current());
    if (new_state == SCAN_STATE) {
      state = new_state;
    }
    else if (new_state == PUSH_NORMAL_STATE) {
      V_output = V_center;
      state = new_state;
    }
  }
  S.printf("state is %i\n", state);
}

void cmd_V_center(qCommand& qC, Stream& S) {
  if (qC.next() != NULL) {
    float new_V_center = atof(qC.current());
    if ((new_V_center <= V_max) && (new_V_center >= V_min)) {
      V_center = new_V_center;
    }
  }
  S.printf("V_center is %f\n", V_center);
}

void cmd_V_scan(qCommand& qC, Stream& S) {
  if (qC.next() != NULL) {
    float new_V_scan = atof(qC.current());
    if ((new_V_scan <= 5.0) && (new_V_scan >= 0.0)) {
      V_scan = new_V_scan;
    }
  }
  S.printf("V_scan is %f\n", V_scan);
}

void cmd_V_push_step(qCommand& qC, Stream& S) {
  if (qC.next() != NULL) {
    V_push_step = atof(qC.current());
  }
  S.printf("V_push_step is %f\n", V_push_step);
}

void cmd_V_output(qCommand& qC, Stream& S) {
  S.printf("V_output is %f\n", V_output);
}

void cmd_adc1_value(qCommand& qC, Stream& S) {
  S.printf("ADC1 voltage is %f\n", adc1_value);
}

void cmd_adc2_data(qCommand& qC, Stream& S) {
  adc2_pause = true;
  if (adc2_ready) {
    for (int i = adc2_index; i < NUM_DATA; i++) {
      S.printf("%f\n", adc2_data[i]);
    }
    for (int i = 0; i < adc2_index; i++) {
      S.printf("%f\n", adc2_data[i]);
    }
  }
  else {
    for (int i = 0; i < adc2_index; i++){
      S.printf("%f\n", adc2_data[i]);
    }
    for (int i = adc2_index; i < NUM_DATA; i++) {
      S.printf("%f\n", 0.0f);
    }
  }
  adc2_ready = false;
  adc2_index = 0;
  adc2_pause = false;
}

void setup(void) {
  configureADC(1, t_push, 0, BIPOLAR_10V, get_adc1);
  configureADC(2, t_error_sample, 0, BIPOLAR_2500mV, get_adc2);
  triggerMode(1, OUTPUT);
  qC.addCommand("state", cmd_state);
  qC.addCommand("vcenter", cmd_V_center);
  qC.addCommand("vscan", cmd_V_scan);
  qC.addCommand("vpushstep", cmd_V_push_step);
  qC.addCommand("voutput", cmd_V_output);
  qC.addCommand("adc1value", cmd_adc1_value);
  qC.addCommand("adc2data", cmd_adc2_data);
}

void loop(){
  qC.readSerial(Serial);  // TODO: check if this parses the full command.
  qC.readSerial(Serial2);
  if (state == SCAN_STATE) {
    scan();
  }
}
