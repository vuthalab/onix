#include "qCommand.h"
#include <math.h>
qCommand qC;

double adc1 = 0; // to store the adc reading
double low_pass = 0; // to store the adc reading after filter is applied

const uint SampleRate = 1; // us

double filter = 10; // Hz, low pass
double y = tan(PI * filter * SampleRate * 1e-6);
double alpha = 2 * y / (y+1); // calculate alpha for this filter

const int DATA_LENGTH = 10; // TODO: Change this before I actually run the code
float data[DATA_LENGTH];
int data_index = 0;

bool running = false;

void cmd_check_filter(qCommand& qC, Stream& S) {
  S.printf("Cutoff: ");
  S.println(filter);
  S.printf("y: ");
  S.println(y, 6);
  S.printf("Alpha: ");
  S.println(alpha, 6);
}

void getADC1() {
  if (running) {
    adc1 = readADC1_from_ISR(); 
    low_pass = alpha * adc1 + (1-alpha) * low_pass;
    writeDAC(1,adc1); // write unfiltered value to DAC1, useful for testing
    writeDAC(2,low_pass); // write filtered value to DAC2, usefult for testing
    data[data_index] = low_pass;

    if (data_index < DATA_LENGTH - 1) {
      data_index++;
    }
    else {
      data_index = 0;
    }

  }
}

void cmd_data(qCommand& qC, Stream& S) {
  running = false;
  for (int i = 0; i < DATA_LENGTH; i++) {
      S.write(data[i]);
    }
  running = true;
}

void cmd_start(qCommand& qC, Stream& S) {
  running = true;
  S.println("started");
}

void cmd_stop(qCommand& qC, Stream& S) {
  running = false;
  S.println("stopped");
}

void setup(void) {
  qC.addCommand("filter", cmd_check_filter);
  qC.addCommand("data", cmd_data);
  qC.addCommand("start", cmd_start);
  qC.addCommand("stop", cmd_stop);
  configureADC(1,SampleRate,0,BIPOLAR_5V,getADC1); // Have ADC take measurement every 2us, ±5V range 
}

void loop() {
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
}
