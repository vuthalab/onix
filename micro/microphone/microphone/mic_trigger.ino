#include "qCommand.h"
#include <math.h>
qCommand qC;

// interval in us for ADC data reading
const uint16_t ADC_INTERVAL = 10;
const uint16_t ADC_DELAY = 0;
const adc_scale_t ADC_SCALE = BIPOLAR_2500mV;


// Data saved in Quarto for computer readout
const int MAX_DATA_LENGTH = 100000;
float data[MAX_DATA_LENGTH];

int data_index = 0;
bool pause_data = false;
float reading = 0;
float low_pass = 0;


// reads data
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

// prints data
void cmd_data(qCommand& qC, Stream& S) {
  pause_data = true;  // pause data taking during process
  int get_data_length = MAX_DATA_LENGTH;
  if (qC.next() != NULL) {
    get_data_length = atoi(qC.current());
  }
  serial_print_data(S, data, data_index, get_data_length);
  pause_data = false;
}

// prints adc interval
void cmd_adc_interval(qCommand& qC, Stream& S) {
  S.print("ADC Interval: ");
  S.println(ADC_INTERVAL);
}

// initial setup
void setup(void) {
  qC.addCommand("data", cmd_data);
  qC.addCommand("adc_interval", cmd_adc_interval);
  configureADC(1, ADC_INTERVAL, ADC_DELAY, ADC_SCALE, adc_loop);
}

// the loop reads from the serial ports every time
void loop() {
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
}
