// Quarto code for digitizing input voltages.

#include "qCommand.h"
#include <math.h>
qCommand qC;

const uint8_t TRIGGER_INPUT_PORT = 2;

const uint16_t ADC_INTERVAL = 1;
const uint16_t ADC_DELAY = 0;
const adc_scale_t ADC_SCALE = BIPOLAR_5V;

double filter = 10; // Hz, low pass
double y = tan(PI * filter * ADC_INTERVAL * 1e-6);
double alpha = 2 * y / (y+1); // calculate alpha for this filter

const int DATA_LENGTH = 100000;
float data[DATA_LENGTH];
int data_index = 0;
int16_t data_read_countdown = 0;

double low_pass = 0;

bool running = false;
bool reading = false;
int trigger_too_soon = 0;

int segment_length = 0;
int segment_number = 0;

void input_1_loop(void) {
  float reading = readADC1_from_ISR();
  if (data_read_countdown > 0) {
    low_pass = alpha * reading + (1-alpha) * low_pass;
    data[data_index] = low_pass;
    data_index++;
    data_read_countdown--;
  }
}

void cmd_trigger(qCommand& qC, Stream& S) {
  if (running) {
    if (data_read_countdown > 0) {
      trigger_too_soon++;
    }
    else {
      data_read_countdown = segment_length;
      S.println("triggered");
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
  if (new_segment_number * new_segment_length <= DATA_LENGTH) {
    segment_length = new_segment_length;
    segment_number = new_segment_number;
    S.printf("segment length is %i, segment number is %i\n", segment_length, segment_number);
  }
  else {
    S.printf("asking for too many data points\n");
  }
}

void cmd_start(qCommand& qC, Stream& S) {
  if (reading || running) {
    S.println("start failed");
  }
  else {
    running = true;
    trigger_too_soon = 0;
    data_index = 0;
    data_read_countdown = 0;
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
    S.println(data_index); 
    for (int i = 0; i < data_index; i++) {
      S.printf("%f\n", data[i]);
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
  qC.addCommand("trigger", cmd_trigger);
  configureADC(1, ADC_INTERVAL, ADC_DELAY, ADC_SCALE, input_1_loop);

}

void loop(){
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
}
