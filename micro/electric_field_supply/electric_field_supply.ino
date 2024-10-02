#include "qCommand.h"
#include <math.h>
qCommand qC;

const uint8_t TRIGGER_INPUT_PORT = 1;
const uint8_t OUTPUT_PORT = 1;

int16_t V_low_machine_unit = 0;
int16_t V_high_machine_unit = 3276;

unsigned long rise_ramp_time_us = 0;
unsigned long fall_ramp_time_us = 0;

unsigned long error_counter = 0;
bool running = false;

unsigned long trigger_time;
const int MAX_PULSE_COUNT = 1000;
unsigned long rise_timestamps_us[MAX_PULSE_COUNT];
unsigned long fall_timestamps_us[MAX_PULSE_COUNT];
int pulse_count = 0;
int current_pulse_index = 0;


void triggered(void) {
  if (running) {
    error_counter++;
  }
  trigger_time = micros();
  current_pulse_index = 0;
  running = true;
}

int16_t float_to_int(float number) {
  return int(number * 32768 / 10.24);
}

float int_to_float(int16_t number) {
  return number * 10.24 / 32768;
}

void cmd_V_low(qCommand& qC, Stream& S) {
  if ( qC.next() != NULL) {
    V_low_machine_unit = float_to_int(atof(qC.current()));
  }
  S.printf("V_low is %f\n", int_to_float(V_low_machine_unit));
}

void cmd_V_high(qCommand& qC, Stream& S) {
  if ( qC.next() != NULL) {
    V_high_machine_unit = float_to_int(atof(qC.current()));
  }
  S.printf("V_high is %f\n", int_to_float(V_high_machine_unit));
}

void cmd_error_counter(qCommand& qC, Stream& S) {
  S.printf("error_counter is %i\n", error_counter);
}

void cmd_rise_ramp_time_us(qCommand& qC, Stream& S) {
  if ( qC.next() != NULL) {
    rise_ramp_time_us = atol(qC.current());
  }
  S.printf("rise_ramp_time_us is %i\n", rise_ramp_time_us);
}

void cmd_fall_ramp_time_us(qCommand& qC, Stream& S) {
  if ( qC.next() != NULL) {
    fall_ramp_time_us = atol(qC.current());
  }
  S.printf("fall_ramp_time_us is %i\n", fall_ramp_time_us);
}

void cmd_remove_all_pulses(qCommand& qC, Stream& S) {
  pulse_count = 0;
  current_pulse_index = 0;
  S.printf("remove_all_pulses successful\n");
}

void cmd_pulse_time_us(qCommand& qC, Stream& S) {
  if ( qC.next() != NULL) {
    rise_timestamps_us[pulse_count] = atol(qC.current());
  }
  else {
    S.printf("pulse_time_us failed with argument 1\n");
    return;
  }
  if ( qC.next() != NULL) {
    fall_timestamps_us[pulse_count] = atol(qC.current());
  }
  else {
    S.printf("pulse_time_us failed with argument 2\n");
    return;
  }
  S.printf("pulse_time_us successful\n");
  pulse_count++;
}

void setup(void) {
  qC.addCommand("V_low", cmd_V_low);
  qC.addCommand("V_high", cmd_V_high);
  qC.addCommand("error_counter", cmd_error_counter);
  qC.addCommand("rise_ramp_time_us", cmd_rise_ramp_time_us);
  qC.addCommand("fall_ramp_time_us", cmd_fall_ramp_time_us);
  qC.addCommand("remove_all_pulses", cmd_remove_all_pulses);
  qC.addCommand("pulse_time_us", cmd_pulse_time_us);
  triggerMode(TRIGGER_INPUT_PORT, INPUT);
  enableInterruptTrigger(TRIGGER_INPUT_PORT, RISING_EDGE, triggered);
}

int16_t get_ramp_output(unsigned long ramp_time_us, bool ramp_up) {
  if (ramp_up) {
    float V_diff = (float) V_high_machine_unit - V_low_machine_unit;
    float V_ramp = V_diff / rise_ramp_time_us * ramp_time_us;
    return (int16_t) V_ramp + V_low_machine_unit;
  }
  else {
    float V_diff = (float) V_low_machine_unit - V_high_machine_unit;
    float V_ramp = V_diff / fall_ramp_time_us * ramp_time_us;
    return (int16_t) V_ramp + V_high_machine_unit;
  }
}

void loop(){
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
  int16_t output = V_low_machine_unit;
  if (running && (pulse_count > 0)) {
    unsigned long current_time = micros();
    unsigned long time_difference = current_time - trigger_time;
    if (time_difference < rise_timestamps_us[current_pulse_index]) {
    }
    else if (time_difference < rise_timestamps_us[current_pulse_index] + rise_ramp_time_us) {
      unsigned long ramp_time_us = time_difference - rise_timestamps_us[current_pulse_index];
      output = get_ramp_output(ramp_time_us, true);
    }
    else if (time_difference < fall_timestamps_us[current_pulse_index]) {
      output = V_high_machine_unit;
    }
    else if (time_difference < fall_timestamps_us[current_pulse_index] + fall_ramp_time_us) {
      unsigned long ramp_time_us = time_difference - fall_timestamps_us[current_pulse_index];
      output = get_ramp_output(ramp_time_us, false);
    }
    else {
      output = V_low_machine_unit;
      current_pulse_index++;
      if (current_pulse_index >= pulse_count) {
        running = false;
      }
    }
  }
  else if (pulse_count == 0) {
    running = false;
  }
  writeDACRAW(OUTPUT_PORT, output);
}
