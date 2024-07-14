#include "qCommand.h"
#include <math.h>
qCommand qC;

// interval in us for ADC data reading
const uint8_t CHANNEL1 = 1;
const uint8_t CHANNEL2 = 2;
const uint8_t CHANNEL3 = 3;
const uint8_t CHANNEL4 = 4;

const uint16_t ADC_INTERVAL = 1E4; // set sampling rate
const uint16_t ADC1_DELAY = 0; // to avoid crashes when multiple channels attempt to take data at the same time, we have a 5 us delay between channels
const uint16_t ADC2_DELAY = 5;
const uint16_t ADC3_DELAY = 10;
const uint16_t ADC4_DELAY = 15;
const adc_scale_t ADC_SCALE = BIPOLAR_10V; // the Mag690-100 can output +-10 V

const int DATA_TIME = 1E7; // save at maximum the last 10 s of data for each channel

// Data saved in Quarto for computer readout
const int MAX_DATA_LENGTH = DATA_TIME / ADC_INTERVAL;
float data1[MAX_DATA_LENGTH];
float data2[MAX_DATA_LENGTH];
float data3[MAX_DATA_LENGTH];
float data4[MAX_DATA_LENGTH];

int output_index = 0;
int data_index1 = 0;
int data_index2 = 0;
int data_index3 = 0;
int data_index4 = 0;

float reading1 = 0;
float reading2 = 0;
float reading3 = 0;
float reading4 = 0;

bool pause_data = false;

void adc1_loop(void) {
  reading1 = readADC1_from_ISR();
  data1[data_index1] = reading1;
  if (data_index1 < MAX_DATA_LENGTH - 1) {
    data_index1++;
  } else {
    data_index1 = 0;
  }
}

void adc2_loop(void) {
  reading2 = readADC2_from_ISR();
  data2[data_index2] = reading2;
  if (data_index2 < MAX_DATA_LENGTH - 1) {
    data_index2++;
  } else {
    data_index2 = 0;
  }
}

void adc3_loop(void) {
  reading3 = readADC3_from_ISR();
  data3[data_index3] = reading3;
  if (data_index3 < MAX_DATA_LENGTH - 1) {
    data_index3++;
  } else {
    data_index3 = 0;
  }
}

void adc4_loop(void) {
  reading4 = readADC4_from_ISR();
  data4[data_index4] = reading4;
  if (data_index4 < MAX_DATA_LENGTH - 1) {
    data_index4++;
  } else {
    data_index4 = 0;
  }
}

void serial_print_data_bytes(Stream& S, float array[], int next_index, int length) {
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
    S.write((byte*)array, num_bytes - bytes_to_end);
  }
  else {
    S.write((byte*)array + start_byte, num_bytes);
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
  if (first_index > last_index) {
    for (int i = first_index; i < MAX_DATA_LENGTH; i++) {
      S.printf("%f\n", array[i]);
    }
    for (int i = 0; i <= last_index; i++) {
      S.printf("%f\n", array[i]);
    }
  }
  else {
    for (int i = first_index; i <= last_index; i++) {
      S.printf("%f\n", array[i]);
    }
  }
}

void cmd_data(qCommand& qC, Stream& S) {
  int last_full_data_index = min(data_index1, min(data_index2, min(data_index3, data_index4))); // largest index of data that all channels have
  int next_index = last_full_data_index + 1;
  if (next_index >= MAX_DATA_LENGTH) {
    next_index = 0;
  }
  int get_data_length = next_index - output_index;
  if (get_data_length <= 0){
    get_data_length += MAX_DATA_LENGTH;
  }
  //S.print("get_data_length C should be ");
  //S.println(get_data_length);
  //S.print("last full data index is ");
  //S.println(last_full_data_index);

  serial_print_data(S, data1, next_index, get_data_length);
  serial_print_data(S, data2, next_index, get_data_length);
  serial_print_data(S, data3, next_index, get_data_length);
  serial_print_data(S, data4, next_index, get_data_length);
  output_index = next_index;
}

void cmd_adc_interval(qCommand& qC, Stream& S) {
  S.print("ADC_INTERVAL: ");
  S.println(ADC_INTERVAL);
  //S.printf("ADC_INTERVAL %i\n", ADC_INTERVAL); // TODO: understand why when I use S.printf lines the data time and max_data length commands work, but adc_interval returns max_data_length
}

void cmd_data_time(qCommand& qC, Stream& S) {
  S.print("DATA_TIME: ");
  S.println(DATA_TIME);
  //S.printf("Data Time: %i\n", DATA_TIME);
}

void cmd_max_data_length(qCommand& qC, Stream& S) {
  S.print("MAX_DATA_LENGTH: ");
  S.println(MAX_DATA_LENGTH);
  //S.printf("Max data length: %i\n", MAX_DATA_LENGTH);
}

void setup(void) {
  qC.addCommand("data", cmd_data);
  qC.addCommand("adc_interval", cmd_adc_interval);
  qC.addCommand("data_time", cmd_data_time);
  qC.addCommand("max_data_length", cmd_max_data_length);
  configureADC(CHANNEL1, ADC_INTERVAL, ADC1_DELAY, ADC_SCALE, adc1_loop);
  configureADC(CHANNEL2, ADC_INTERVAL, ADC2_DELAY, ADC_SCALE, adc2_loop);
  configureADC(CHANNEL3, ADC_INTERVAL, ADC3_DELAY, ADC_SCALE, adc3_loop);
  configureADC(CHANNEL4, ADC_INTERVAL, ADC4_DELAY, ADC_SCALE, adc4_loop);
}

void loop() {
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
}
