// Quarto code for digitizing input voltages.

#include "qCommand.h"
#include <math.h>
qCommand qC;

const uint8_t TRIGGER_INPUT_PORT = 1;

const uint16_t ADC_INTERVAL = 1;
const uint16_t ADC_DELAY = 0;
const uint16_t ADC_SCALE = BIPOLAR_2500mV;

const int DATA_LENGTH = 50000;
float data_1[DATA_LENGTH];
int data_index_1 = 0;
int16_t data_1_read_countdown = 0;
float data_2[DATA_LENGTH];
int data_index_2 = 0;
int16_t data_2_read_countdown = 0;

bool running = false;
bool reading = false;
int trigger_too_soon = 0;

int segment_length = 0;
int segment_number = 0;


void input_1_loop(void) {
  float reading = readADC1_from_ISR();
  if (data_1_read_countdown > 0) {
    data_1[data_index_1] = reading;
    data_index_1++;
    data_1_read_countdown--;
  }
}

void input_2_loop(void) {
  float reading = readADC2_from_ISR();
  if (data_2_read_countdown > 0) {
    data_2[data_index_2] = reading;
    data_index_2++;
    data_2_read_countdown--;
  }
}

void triggered(void) {
  if (running) {
    if (data_1_read_countdown > 0) {
      trigger_too_soon++;
    }
    else {
      data_1_read_countdown = segment_length;
    }
    if (data_2_read_countdown > 0) {
      trigger_too_soon++;
    }
    else {
      data_2_read_countdown = segment_length;
    }
  }
}

void cmd_setup(qCommand& qC, Stream& S) {
  int new_segment_length = segment_length;
  int new_segment_number = segment_number;
  if ( qC.next() != NULL) {
    new_segment_length = atoi(qC.current());
  }
  if ( qC.next() != NULL) {
    new_segment_number = atoi(qC.current());
  }
  if (new_segment_number * new_segment_number <= DATA_LENGTH) {
    segment_length = new_segment_length;
    segment_number = new_segment_number;
  }
  S.printf("segment length is %i, segment number is %i\n", segment_length, segment_number);
}

void cmd_start(qCommand& qC, Stream& S) {
  if (reading || running) {
    S.println("start failed");
  }
  else {
    running = true;
    trigger_too_soon = 0;
    data_index_1 = 0;
    data_index_2 = 0;
    data_1_read_countdown = 0;
    data_2_read_countdown = 0;
    S.println("started");
  }
}

void cmd_stop(qCommand& qC, Stream& S) {
  if (reading || !running) {
    S.println("stop failed");
  }
  else {
    running = false;
    S.println("stopped");
  }
}

void cmd_trigger_too_soon(qCommand& qC, Stream& S) {
  S.printf("triggers too soon is %i\n", trigger_too_soon);
}

void cmd_data(qCommand& qC, Stream& S) {
  reading = true;
  if (running) {
    S.println(0);
    S.println(0);
  }
  else {
    S.println(data_index_1);
    for (int i = 0; i < data_index_1; i++) {
      S.println(data_1[i], 6);
    }
    S.println(data_index_2);
    for (int i = 0; i < data_index_2; i++) {
      S.println(data_2[i], 6);
    }
  }
  reading = false;
}

void setup(void) {
  qC.addCommand("setup", cmd_setup);
  qC.addCommand("start", cmd_start);
  qC.addCommand("stop", cmd_stop);
  qC.addCommand("trigger_too_soon", cmd_trigger_too_soon);
  qC.addCommand("data", cmd_data);
  configureADC(1, ADC_INTERVAL, ADC_DELAY, ADC_SCALE, input_1_loop);
  configureADC(2, ADC_INTERVAL, ADC_DELAY, ADC_SCALE, input_2_loop);
  triggerMode(TRIGGER_INPUT_PORT, INPUT);
  enableInterruptTrigger(TRIGGER_INPUT_PORT, RISING_EDGE, triggered);
}

void loop(){
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
}
