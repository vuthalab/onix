// Quarto code for 1-channel PID feedback for laser intensity stabilization.
// Blue LED is on when feedback is on.

#include "qCommand.h"
#include <math.h>
qCommand qC;

// laser diode voltage input port
const uint8_t PRIMARY_LD_INPUT = 1;
const uint8_t MONITOR_LD_INPUT = 2;
// control signal output port
const uint8_t CONTROL_OUTPUT = 1;

// interval in us for ADC data reading.
// Shorter interval will cause the program to freeze due to too many ADC reading requests.
// Longer interval slow down the PID loop.
uint16_t adc_interval = 2; 
const uint16_t ADC_DELAY = 0;
const adc_scale_t ADC_SCALE = BIPOLAR_5V;

float p_gain = -0.1;
float i_time = 1;  // us
float d_time = 20.0;  // us

// keeps track of the integral term
float integral = 0.0;
// limits the integral term magnitude so it does not blow up
float integral_limit = 10.0;
float current_ld_reading = 0.0;
// last error signal for D gain.
float previous_ld_reading = -100.0;

// error signal offset before going into the PID loop
float primary_ld_setpoint = 3.8;

// output voltage offset
float output_offset = 9.0;
// output voltage limits
float output_lower_limit = 0.0;
float output_upper_limit = 9.0;

float acceptable_output_range = output_upper_limit - output_lower_limit;
float output_lower_warning = output_lower_limit + 0.1 * acceptable_output_range;
float output_upper_warning = output_upper_limit - 0.1 * acceptable_output_range;

float acceptable_integral_range = 2 * integral_limit;
float integral_lower_warning = -integral_limit + 0.1 * acceptable_integral_range;
float integral_upper_warning = integral_limit - 0.1 * acceptable_integral_range;

// PID state
// 0: off
// 1: continuous feedback on
int pid_state = 0;

// Data saved in Quarto for computer readout
const int MAX_DATA_LENGTH = 30000;
int data_length = MAX_DATA_LENGTH;
float primary_ld_data[MAX_DATA_LENGTH];
float monitor_ld_data[MAX_DATA_LENGTH];
int ld_index = 0;
bool pause_ld_data = false;
float output_data[MAX_DATA_LENGTH];
int output_index = 0;
bool pause_output_data = false;


void primary_ld_loop(void) {
  switch (PRIMARY_LD_INPUT) {
    case 1:
      current_ld_reading = readADC1_from_ISR();
      break;
    case 2:
      current_ld_reading = readADC2_from_ISR();
      break;
    case 3:
      current_ld_reading = readADC3_from_ISR();
      break;
    case 4:
      current_ld_reading = readADC4_from_ISR();
      break;
  }
  update_pid();  // this function must be fast compared to the ADC sample interval.
}

void monitor_ld_loop(void) {
  float monitor_ld_reading;
  switch (MONITOR_LD_INPUT) {
    case 1:
      monitor_ld_reading = readADC1_from_ISR();
      break;
    case 2:
      monitor_ld_reading = readADC2_from_ISR();
      break;
    case 3:
      monitor_ld_reading = readADC3_from_ISR();
      break;
    case 4:
      monitor_ld_reading = readADC4_from_ISR();
      break;
  }
  if (!pause_ld_data) {
    monitor_ld_reading[ld_index] = monitor_ld_reading;
    if (ld_index < data_length - 1) {
      ld_index++;
    }
    else {
      ld_index = 0;
    }
  }
}

float new_integral(float integral, float integral_change) {
  // limit the integral term to be within the limit.
  float pending_integral = integral + integral_change;
  if (pending_integral > integral_limit) {
    return integral_limit;
  }
  else if (pending_integral < -integral_limit) {
    return -integral_limit;
  }
  return pending_integral;
}

void update_pid(void) {
  // takes ~1 us to finish. Safe to put it in the ADC loop with ~2 us interval.
  float output = output_offset;
  bool feedback_on = false;
  switch (pid_state) {
    case 0:  // feedback off
      break;
    case 1:  // continuous feedback
      feedback_on = true;
      break;
    default:
      break;
  }
  if (feedback_on) {
    float error = current_ld_reading - primary_ld_setpoint;
    float proportional = p_gain * error;
    integral = new_integral(integral, p_gain * adc_interval / i_time * error);
    float differential = 0.0;
    if (previous_ld_reading > -99.0) {  // not the first data point.
      differential = p_gain * d_time / adc_interval * (current_ld_reading - previous_ld_reading);
    }
    previous_ld_reading = error + primary_ld_setpoint;

    output += proportional + integral + differential;
    if (output > output_upper_limit) {
      output = output_upper_limit;
    }
    else if (output < output_lower_limit) {
      output = output_lower_limit;
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
    adc_interval = atoi(qC.current());
    disableADC(PRIMARY_LD_INPUT);
    disableADC(MONITOR_LD_INPUT);
    configureADC(PRIMARY_LD_INPUT, adc_interval, ADC_DELAY, ADC_SCALE, primary_ld_loop);
    configureADC(MONITOR_LD_INPUT, adc_interval, ADC_DELAY, ADC_SCALE, monitor_ld_loop);
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
  acceptable_integral_range = 2 * integral_limit;
  integral_lower_warning = -integral + 0.1 * acceptable_integral_range;
  integral_upper_warning = integral - 0.1 * acceptable_integral_range;
}

void cmd_ld_setpoint(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    primary_ld_setpoint = atof(qC.current());
  }
  S.printf("ld setpoint is %f\n", primary_ld_setpoint);
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
  acceptable_output_range = output_upper_limit - output_lower_limit;
  output_lower_warning = output_lower_limit + 0.1 * acceptable_output_range;
  output_upper_warning = output_upper_limit - 0.1 * acceptable_output_range;
}

void cmd_output_upper_limit(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    output_upper_limit = atof(qC.current());
  }
  S.printf("output upper limit is %f\n", output_upper_limit);
  acceptable_output_range = output_upper_limit - output_lower_limit;
  output_lower_warning = output_lower_limit + 0.1 * acceptable_output_range;
  output_upper_warning = output_upper_limit - 0.1 * acceptable_output_range;
}

void cmd_integral(qCommand& qC, Stream& S){
  S.printf("integral term is %f\n", integral);
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
  previous_ld_reading = -100.0;
  S.printf("pid state is %i\n", pid_state);
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

void cmd_primary_ld_data(qCommand& qC, Stream& S){
  pause_ld_data = true; // pause data taking during process
  int get_data_length = MAX_DATA_LENGTH;
  if ( qC.next() != NULL) {
    get_data_length = atoi(qC.current());
  }
  serial_print_data(S, primary_ld_data, ld_index, get_data_length);
  pause_ld_data = false;
}

void cmd_monitor_ld_data(qCommand& qC, Stream& S){
  pause_ld_data = true; // pause data taking during process
  int get_data_length = MAX_DATA_LENGTH;
  if ( qC.next() != NULL) {
    get_data_length = atoi(qC.current());
  }
  serial_print_data(S, monitor_ld_data, ld_index, get_data_length);
  pause_ld_data = false;
}

void cmd_both_ld_data(qCommand& qC, Stream& S){
  pause_ld_data = true; // pause data taking during process
  int get_data_length = MAX_DATA_LENGTH;
  if ( qC.next() != NULL) {
    get_data_length = atoi(qC.current());
  }
  serial_print_data(S, primary_ld_data, ld_index, get_data_length);
  serial_print_data(S, monitor_ld_data, ld_index, get_data_length);
  pause_ld_data = false;
}

void cmd_output_data(qCommand& qC, Stream& S){
  pause_output_data = true; // pause data taking during process
  int get_data_length = MAX_DATA_LENGTH;
  if ( qC.next() != NULL) {
    get_data_length = atoi(qC.current());
  }
  serial_print_data(S, output_data, output_index, get_data_length);
  pause_output_data = false;
}

void cmd_limit_warnings(qCommand& qC, Stream& S) {
  float output = output_data[output_index];

  int indicator = 0;
  if ((output >= output_upper_limit) || (output <= output_lower_limit)) {
      indicator |= (1 << 3); // change the appropriate bit, performs indicator = indicator | 1<<3 which should place a 1 in the 4th bit of indicator
    }
  else if ((output < output_lower_warning) || (output > output_upper_warning)) {
    indicator |= (1 << 2);
  }
  if (integral >= integral_limit || integral <= -integral_limit) {
      indicator |= (1 << 1); 
    }
  else if ((integral < integral_lower_warning) || (integral > integral_upper_warning)) {
    indicator |= (1 << 0);
  }
  S.print("Indicator is "); 
  S.println(indicator);
}

void setup(void) {
  qC.addCommand("p_gain", cmd_p_gain);
  qC.addCommand("i_time", cmd_i_time);
  qC.addCommand("d_time", cmd_d_time);
  qC.addCommand("integral_limit", cmd_integral_limit);
  qC.addCommand("ld_setpoint", cmd_ld_setpoint);
  qC.addCommand("output_offset", cmd_output_offset);
  qC.addCommand("output_lower_limit", cmd_output_lower_limit);
  qC.addCommand("output_upper_limit", cmd_output_upper_limit);
  qC.addCommand("pid_state", cmd_pid_state);
  qC.addCommand("primary_ld_data", cmd_primary_ld_data);
  qC.addCommand("monitor_ld_data", cmd_monitor_ld_data);
  qC.addCommand("both_ld_data", cmd_both_ld_data);
  qC.addCommand("output_data", cmd_output_data);
  qC.addCommand("adc_interval", cmd_adc_interval);
  qC.addCommand("limit_warnings", cmd_limit_warnings);
  qC.addCommand("integral", cmd_integral);
  configureADC(PRIMARY_LD_INPUT, adc_interval, ADC_DELAY, ADC_SCALE, primary_ld_loop);
  configureADC(MONITOR_LD_INPUT, adc_interval, ADC_DELAY, ADC_SCALE, monitor_ld_loop);
}

void loop(){
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
}
