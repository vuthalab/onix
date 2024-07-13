#include "qCommand.h"
#include <math.h>
qCommand qC;

// interval in us for ADC data reading
const uint16_t ADC_INTERVAL = 1E5; // take a data point every 0.1 s
const uint16_t ADC_DELAY = 0;
const adc_scale_t ADC_SCALE = BIPOLAR_10V; // the magnetometer can output +-10 V

const uint16_t DATA_TIME = 1E6; // how long to take data

// Data saved in Quarto for computer readout
const int MAX_DATA_LENGTH = DATA_TIME / ADC_INTERVAL;
float data[MAX_DATA_LENGTH];

int data_index = 0;
bool pause_data = false;
float reading = 0;

void adc_loop(void) {
  reading = readADC1_from_ISR();
  bool local_pause_data = pause_data;
  if (!local_pause_data) {
    data[data_index] = reading;
  }
  if (!local_pause_data) {
    if (data_index < MAX_DATA_LENGTH - 1) {
      data_index++;
    } else {
      data_index = 0;
    }
  }
}

void serial_print_data(Stream& S, float array[], int next_index, int length) {
  if (length < 0) {
    return;
  }
  int last_index = next_index - 1;
  if (last_index < 0) {
    last_index += MAX_DATA_LENGTH;
  }
  int first_index = last_index - length + 1;
  if (first_index < 0) {
    first_index += MAX_DATA_LENGTH;
  }
  
  int num_bytes = 4 * length;
  int start_byte = 4 * first_index;
  int bytes_to_end = 4 * (MAX_DATA_LENGTH - first_index);

  if (first_index > last_index) {
    S.write((byte*)array + start_byte, bytes_to_end);
    //S.write(*array + start_byte, bytes_to_end);
    S.write((byte*)array, num_bytes - bytes_to_end);
  }
  else {
    S.write((byte*)array + start_byte, num_bytes);
  }
}

void cmd_data(qCommand& qC, Stream& S) {
  pause_data = true;  // pause data taking during process
  int get_data_length = MAX_DATA_LENGTH;
  if (qC.next() != NULL) {
    get_data_length = atoi(qC.current());
  }
  serial_print_data(S, data, data_index, get_data_length);
  pause_data = false;
}

void cmd_adc_interval(qCommand& qC, Stream& S) {
  S.print("ADC Interval: ");
  S.println(ADC_INTERVAL);
}

void cmd_data_time(qCommand& qC, Stream& S) {
  S.print("Data Time: ");
  S.println(DATA_TIME);
}

void setup(void) {
  qC.addCommand("data", cmd_data);
  qC.addCommand("adc_interval", cmd_adc_interval);
  qC.addCommand("data_time", cmd_data_time);
  configureADC(1, ADC_INTERVAL, ADC_DELAY, ADC_SCALE, adc_loop);
}

void loop() {
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
}
