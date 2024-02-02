// Quarto code for 1-channel PID feedback.
// Blue LED is on when feedback is on.

#include "qCommand.h"
#include <math.h>
qCommand qC;

// error signal input port
const uint8_t ERROR_INPUT = 1;
// trigger input port for enabling PID.
const uint8_t PID_PULSE_TRIGGER = 2;
// control signal output port
const uint8_t CONTROL_OUTPUT = 1;

// interval in us for ADC data reading.
// Shorter inverval will cause the program to freeze due to too many ADC reading requests.
// Longer interval slow down the PID loop.
uint16_t adc_interval = 2; 
const uint16_t ADC_DELAY = 0;
const adc_scale_t ADC_SCALE = BIPOLAR_5V;

float p_gain = 1.0;
float i_time = 100.0;  // us
float d_time = 0.0;  // us

// keeps track of the integral term
float integral = 0.0;
// limits the integral term magnitude so it does not blow up
float integral_limit = 10.0;
float current_error = 0.0;
// last error signal for D gain.
float previous_error = -100.0;

// error signal offset before going into the PID loop
float error_offset = 0.3;

// output voltage offset
float output_offset = 10.0;
// output voltage limits
float output_lower_limit = 0.0;
float output_upper_limit = 10.0;

// byte to store information as to how close we are to reaching integral and output limits
uint8_t indicator = B00000000;
float acceptable_output_range = output_upper_limit - output_lower_limit;
float output_lower_warning = output_lower_limit + 0.1 * acceptable_output_range;
float output_upper_warning = output_upper_limit - 0.1 * acceptable_output_range;

float acceptable_integral_range = 2 * integral_limit;
float integral_lower_warning = -integral_lower_limit + 0.1 * acceptable_integral_range;
float integral_upper_warning = integral_lower_limit - 0.1 * acceptable_integral_range;

// PID state
// 0: off
// 1: continuous feedback on
// 2: pulsed feedback on (controlled by trigger)
int pid_state = 0;
// Output error (every nonzero bit corresponds to an error)
// bit 0: integral term is railed
// bit 1: output is railed
int output_error = 0;
bool pid_trigger_high = false;

// Data saved in Quarto for computer readout
const int MAX_DATA_LENGTH = 50000;
int data_length = MAX_DATA_LENGTH;
float error_data[MAX_DATA_LENGTH];
int error_index = 0;
bool pause_error_data = false;
float output_data[MAX_DATA_LENGTH];
int output_index = 0;
bool pause_output_data = false;
int get_data_length = MAX_DATA_LENGTH


void adc_loop(void) {
  current_error = readADC1_from_ISR();
  if (!pause_error_data) {
    error_data[error_index] = current_error;
    if (error_index < data_length - 1) {
      error_index++;
    }
    else {
      error_index = 0;
    }
  }
  update_pid();  // this function must be fast compared to the ADC sample interval.
}

float new_integral(float integral, float integral_change) {
  // limit the integral term to be within the limit.
  float pending_integral = integral + integral_change;
  if (pending_integral > integral_limit) {
    output_error = output_error | 1;
    return integral_limit;
  }
  else if (pending_integral < -integral_limit) {
    output_error = output_error | 1;
    return -integral_limit;
  }
  else {
    if (output_error & 1) {
      output_error -= 1;
    }
    return pending_integral;
  }
}

void update_pid(void) {
  // takes ~1 us to finish. Safe to put it in the ADC loop with ~2 us interval.
  float output = output_offset;
  bool feedback_on = false;
  switch (pid_state) {
    case 0:  // feedback off
      integral = 0.0;
      previous_error = -100.0;
      break;
    case 1:  // continuous feedback
      feedback_on = true;
      break;
    case 2:  // pulsed feedback
      if (!pid_trigger_high) {
        output = 0.0;
        previous_error = -100.0;
      }
      else {
        feedback_on = true;
      }
      break;
    default:
      break;
  }
  if (feedback_on) {
    float error = current_error - error_offset;
    float proportional = p_gain * error;
    integral = new_integral(integral, p_gain * adc_interval / i_time * error);
    float differential = 0.0;
    if (previous_error > -99.0) {  // not the first data point.
      differential = p_gain * d_time / adc_interval * (current_error - previous_error);
    }
    previous_error = error + error_offset;

    output += proportional + integral + differential;
    if (output > output_upper_limit) {
      output = output_upper_limit;
      output_error = output_error | 2;
    }
    else if (output < output_lower_limit) {
      output = output_lower_limit;
      output_error = output_error | 2;
    }
    else {
      if (output_error & 2) {
        output_error -= 2;
      }
    }
  }
  writeDAC(CONTROL_OUTPUT, output);

  if (!pause_output_data) {
    output_data[output_index] = output;
    if (output_index < data_length - 1) {
      output_index++;
    }
    else {
      output_index = 0;
    }
  }
}

void cmd_adc_interval(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    adc_interval = atoi(qC.current()); // string to uint16_t?
    disableADC(ERROR_INPUT);
    configureADC(ERROR_INPUT, adc_interval, ADC_DELAY, ADC_SCALE, adc_loop);
  }
  S.printf("adc interval is %u\n", (unsigned int)adc_interval);
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
  }
  if (pid_state == 1) {
    setLEDBlue(true);
  }
  else {
    setLEDBlue(false);
  }
  integral = 0.0;
  previous_error = -100.0;
  S.printf("pid state is %i\n", pid_state);
}

void cmd_get_data_length(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    get_data_length = atoi(qC.current());
  }
  S.printf("get_data_length is %i\n", get_data_length);
}

// Check this- if correct use the same on cmd_output_data
void cmd_error_data(qCommand& qC, Stream& S){
  pause_error_data = true; // pause data taking during process
  end_data_index = get_data_length + error_index;
  if (end_data_index > data_length) {
    for (int i = error_index; i < data_length; i++) { 
    S.printf("%f\n", error_data[i]);
  }
  for (int i = 0; i < get_data_length - data_length + error_index ; i++) {
    S.printf("%f\n", error_data[i]);
  }
  pause_error_data = false;
}
  else{
    for (int i = error_index; i <= error_index + get_data_length; i++) { 
    S.printf("%f\n", error_data[i]);
  }
  pause_error_data = false;
  }
}

void cmd_output_data(qCommand& qC, Stream& S){
  pause_output_data = true; // pause data taking during process
  for (int i = output_index; i < data_length; i++) {
    S.printf("%f\n", output_data[i]);
  }
  for (int i = 0; i < output_index; i++) {
    S.printf("%f\n", output_data[i]);
  }
  pause_output_data = false;
}

// Check this
void cmd_limit_warnings(qCommand& qC, Stream& S){
  // look at the integral and output limits warnings and print the appropriate number
  // do these bit numbers 0 or 1 index (here i assume they 1 index)
  if (output > output_upper_limit || output < output_lower_limit) {
      indicator |= (1 << 5); // change the appropriate bit, performs indicator = indicator | 1<<5 which should place a 1 in the 6th place of indicator
    }
  if ( (output < output_lower_warning && output > output_lower_limit) || (output > output_upper_warning && output < output_upper_limit) ) {
    indicator |= (1 << 4);
  }
  if (output <= output_upper_warning && output >= output_lower_warning){
      indicator |= (1 << 3);
  }
  if (integral > integral_limit || integral < -integral_limit) {
      indicator |= (1 << 2); 
    }
  if ( (integral < integral_lower_warning && integral > -integral_limit) || (integral > integral_upper_warning && integral < integral_limit) ) {
    indicator |= (1 << 1);
  }
  if (integral <= integral_upper_warning && integral >= integral_lower_warning){
      indicator |= (1 << 0);
  }
  S.print("Indicator bit is "); 
  S.println(indicator);
  indicator = B00000000 // need to reset the byte when done, no idea if this actally works
}

void pid_pulse_rising(void) {
  pid_trigger_high = true;
  if (pid_state == 2) {
    setLEDBlue(true);
  }
}

void pid_pulse_falling(void) {
  pid_trigger_high = false;
  if (pid_state == 2) {
    setLEDBlue(false);
  }
}

void pid_pulse(void) {
  bool state = triggerRead(PID_PULSE_TRIGGER);
  pid_trigger_high = state;
  if (pid_state == 2) {
    setLEDBlue(state);
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
  qC.addCommand("adc_interval", cmd_adc_interval);
  qC.addCommand("limit_warnings", cmd_limit_warnings);
  configureADC(ERROR_INPUT, adc_interval, ADC_DELAY, ADC_SCALE, adc_loop);
  triggerMode(PID_PULSE_TRIGGER, INPUT);
  enableInterruptTrigger(PID_PULSE_TRIGGER, BOTH_EDGES, pid_pulse);  // TODO: read trigger state when started.
}

void loop(){
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
}
