// Quarto code for 1-channel PID feedback.

#include "qCommand.h"
#include <math.h>
qCommand qC;

// error signal input port
const uint8_t ERROR_INPUT = 1;
// control signal output port
const uint8_t CONTROL_OUTPUT = 1;

// interval in us for ADC data reading.
// Shorter inverval will cause the program to freeze due to too many ADC reading requests.
// Longer interval slow down the PID loop.
const uint16_t ADC_INTERVAL = 10;
const uint16_t ADC_DELAY = 0;
const adc_scale_t ADC_SCALE = BIPOLAR_2500mV;

double p_gain = 0.1;
double i_time = 900.0;
double d_time = 0.0;

// keeps track of the integral term
double integral = 0.0;
// limits the integral term magnitude so it does not blow up
double integral_limit = 10.0;
// last error signal for D gain.
double previous_error = 0.0;

// error signal offset before going into the PID loop
double error_offset = 1.5;

// output voltage offset
double output_offset = 0.0;
// output voltage limits
double output_lower_limit = 0.0;
double output_upper_limit = 10.0;

// PID loop running or not
bool pid_state = false;

// Data saved in Quarto for computer readout
const int DATA_LENGTH = 1000;
double error_data[DATA_LENGTH];
int error_index = 0;
double output_data[DATA_LENGTH];
int output_index = 0;


void adc_loop(void) {
  error_data[error_index] = readADC1_from_ISR();
  if (error_index < DATA_LENGTH) {
    error_index++;
  }
  else {
    error_index = 0;
  }
  delayMicroseconds(1);
  //update_pid();  // this function must be fast compared to the ADC sample interval.
}

double new_integral(double integral, double integral_change) {
  // limit the integral term to be within the limit.
  double pending_integral = integral + integral_change;
  if (pending_integral > integral_limit) {
    return integral_limit;
  }
  else if (pending_integral < -integral_limit) {
    return -integral_limit;
  }
  else {
    return pending_integral;
  }
}

void update_pid(void) {
  // takes <1 us to finish. Safe to put it in the ADC loop with ~3 us interval.
  double output = output_offset;
  if (pid_state) {
    double error = error_data[error_index] - error_offset;
    double proportional = p_gain * error;
    integral = new_integral(integral, p_gain / i_time * error);
    double differential = p_gain * d_time * (error - previous_error);
    previous_error = error;

    output += proportional + integral + differential;
    if (output > output_upper_limit) {
      output = output_upper_limit;
    }
    else if (output < output_lower_limit) {
      output = output_lower_limit;
    }
  }
  writeDAC(CONTROL_OUTPUT, output);

  output_data[output_index] = output;
  if (output_index < DATA_LENGTH) {
    output_index++;
  }
  else {
    output_index = 0;
  }
}

void cmd_p_gain(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    p_gain = atof(qC.current());
  }
  S.printf("p gain is %f\n", p_gain);
}

void cmd_i_time(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    i_time = atof(qC.current());
  }
  S.printf("i time is %f\n", i_time);
}

void cmd_d_time(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    d_time = atof(qC.current());
  }
  S.printf("d time is %f\n", d_time);
}

void cmd_integral_limit(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    integral_limit = atof(qC.current());
  }
  S.printf("integral limit is %f\n", integral_limit);
}

void cmd_error_offset(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    error_offset = atof(qC.current());
  }
  S.printf("error offset is %f\n", error_offset);
}

void cmd_output_offset(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    output_offset = atof(qC.current());
  }
  S.printf("output offset is %f\n", output_offset);
}

void cmd_output_lower_limit(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    output_lower_limit = atof(qC.current());
  }
  S.printf("output lower limit is %f\n", output_lower_limit);
}

void cmd_output_upper_limit(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    output_upper_limit = atof(qC.current());
  }
  S.printf("output upper limit is %f\n", output_upper_limit);
}

void cmd_pid_state(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    pid_state = atoi(qC.current());
    if (pid_state) {
      integral = 0.0;
    }
  }
  S.printf("pid state is %i\n", pid_state);
}

void cmd_error_data(qCommand& qC, Stream& S){
  for (int i = error_index; i < DATA_LENGTH; i++) {
    S.printf("%f\n", error_data[i]);
  }
  for (int i = 0; i < error_index; i++) {
    S.printf("%f\n", error_data[i]);
  }
}

void cmd_output_data(qCommand& qC, Stream& S){
  for (int i = output_index; i < DATA_LENGTH; i++) {
    S.printf("%f\n", output_data[i]);
  }
  for (int i = 0; i < output_index; i++) {
    S.printf("%f\n", output_data[i]);
  }
}

void setup(void) {
  qC.addCommand("p_gain", cmd_p_gain);
  qC.addCommand("i_time", cmd_i_time);
  qC.addCommand("d_time", cmd_d_time);
  qC.addCommand("integral_limit", cmd_integral_limit);
  qC.addCommand("error_offset", cmd_error_offset);
  qC.addCommand("output_offset", cmd_output_offset);
  qC.addCommand("output_lower_limit", cmd_output_lower_limit);
  qC.addCommand("output_upper_limit", cmd_output_upper_limit);
  qC.addCommand("pid_state", cmd_pid_state);
  qC.addCommand("error_data", cmd_error_data);
  qC.addCommand("output_data", cmd_output_data);
  configureADC(ERROR_INPUT, ADC_INTERVAL, ADC_DELAY, ADC_SCALE, adc_loop);
}

void loop(){
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
  update_pid();  // this function must be fast compared to the ADC sample interval.
}
