/**
 * Quarto code for laser piezo control.
 * It is designed to work with the Vescent D2-125 servo which provides fast
 * but small-range feedback to the laser (current or AOM).
 * The output monitor from the Vescent goes into the Quarto error input,
 * and Quarto adjusts the piezo to provide slow feedback to keep the error input stable.
 * The Quarto lock trigger output should be connected to relative jump TTL input of the Vescent.
 * NOTE: the wavemeter input and feedback is not implemented yet.
 * An optional wavemeter input can be used. When the wavemeter input deviates
 * from the preset value, Quarto determines that laser has unlocked
 * and disengages the Vescent lock using the lock output TTL. It then adjusts the piezo
 * to adjust the wavemeter input to its preset value and tries to engage the lock again.
 *
 * The quarto has three states:
 * State 0: Quarto output offset and scan can be changed. The lock trigger
 * output is high (unlocked) in this state.
 * State 1: Quarto stops scanning, and changes the lock trigger output to
 * low (locked). It also provides PID feedback to the output offset
 * to keep error input at the last reading in state 0.
 * State 2: In addition to the behavior in state 1, if the wavemeter
 * input drifts away from last input value in state 1 by more than
 * the max_wavemeter_offset, it changes the lock trigger output to high (unlocked),
 * and adjusts the output offset until the wavemeter input is within the max wavemeter offset
 * of the previous input value in state 1. Then it changes lock trigger to
 * low (locked) and restarts the PID feedback to the output offset.
*/

#include "qCommand.h"
#include <math.h>
qCommand qC;

// error signal analog input port
const uint8_t ERROR_INPUT = 1;
// wavemeter signal analog input port
const uint8_t WAVEMETER_INPUT = 2;
// control signal analog output port
const uint8_t CONTROL_OUTPUT = 1;
// laser jump amplitude analog output port
const uint8_t LASER_JUMP_OUTPUT = 2;
// scan signal TTL trigger port
const uint8_t SCAN_TRIGGER_OUTPUT = 1;
// lock engage signal TTL output port
const uint8_t LOCK_TRIGGER_OUTPUT = 2;

// interval in us for ADC data reading
const uint16_t ERROR_ADC_INTERVAL = 10;  // related to the scan time in state 0.
const uint16_t WAVEMETER_ADC_INTERVAL = 10;
const uint16_t ADC_DELAY = 0;
const adc_scale_t ERROR_ADC_SCALE = BIPOLAR_10V;
const adc_scale_t WAVEMETER_ADC_SCALE = BIPOLAR_10V;

// scan steps (SCAN_STEPS * ERROR_ADC_INTERVAL = scan time)
const int SCAN_STEPS = 1000;

// PID parameters for piezo feedback to the error signal
float p_gain = 0.001;
float i_time = 10000.0;  // us
float d_time = 0.0;  // us

// error signal offset
float error_offset = 6.0;
// keeps track of the integral term
float integral = 0.0;
// limits the integral term magnitude so it does not blow up
float integral_limit = 10.0;
float current_error = 0.0;
// last error signal for D gain.
float previous_error = -100.0;

// PI parameters for piezo feedback to the wavemeter signal
float p_gain_wm = 0.000001;
float i_time_wm = 1000000.0;  // us

// wavemeter error signal and integral term
float error_offset_wm = 0.0;
float current_error_wm = 0.0;
float integral_wm = 0.0;

// output voltage offset
float output_offset = 5.0;
// output voltage scan
float output_scan = 1.0;
int output_scan_index = 0;
// output voltage limits
float output_lower_limit = 0.0;
float output_upper_limit = 10.0;

float acceptable_output_range = output_upper_limit - output_lower_limit;
float output_lower_warning = output_lower_limit + 0.1 * acceptable_output_range;
float output_upper_warning = output_upper_limit - 0.1 * acceptable_output_range;

float acceptable_integral_range = 2 * integral_limit;
float integral_lower_warning = -integral_limit + 0.1 * acceptable_integral_range;
float integral_upper_warning = integral_limit - 0.1 * acceptable_integral_range;

int state = 0;

// Data saved in Quarto for computer readout
const int MAX_DATA_LENGTH = 1000;
int data_length = MAX_DATA_LENGTH;
float error_data[MAX_DATA_LENGTH];
int error_index = 0;
bool pause_error_data = false;
float output_data[MAX_DATA_LENGTH];
int output_index = 0;
bool pause_output_data = false;


void error_adc_loop(void) {
  switch (ERROR_INPUT) {
    case 1:
      current_error = readADC1_from_ISR();
      break;
    case 2:
      current_error = readADC2_from_ISR();
      break;
    case 3:
      current_error = readADC3_from_ISR();
      break;
    case 4:
      current_error = readADC4_from_ISR();
      break;
  }
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

void wavemeter_adc_loop(void) {
  switch (WAVEMETER_INPUT) {
    case 1:
      current_error_wm = readADC1_from_ISR();
      break;
    case 2:
      current_error_wm = readADC2_from_ISR();
      break;
    case 3:
      current_error_wm = readADC3_from_ISR();
      break;
    case 4:
      current_error_wm = readADC4_from_ISR();
      break;
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

bool is_wavemeter_correct(void) {
  return true;  // TODO: check wavemeter output is correct.
}

void update_pid(void) {
  bool scan_on = false;
  bool feedback_on = false;
  bool wm_feedback_on = false;  // TODO: implement wavemeter feedback.
  switch (state) {
    case 0:  // feedback off
      integral = 0.0;
      previous_error = -100.0;
      scan_on = true;
      break;
    case 1:  // feedback on always
      feedback_on = true;
      break;
    case 2:
      if (is_wavemeter_correct()) {
        feedback_on = true;
        break;
      }
      else {
        wm_feedback_on = true;
      }
    default:
      break;
  }
  float output = output_offset;
  if (scan_on) {
    output = output_offset + (float(output_scan_index) / SCAN_STEPS * 2 - 1) * output_scan;
    if (output_scan_index == 0) {
      triggerWrite(SCAN_TRIGGER_OUTPUT, LOW);
    }
    else if (output_scan_index == SCAN_STEPS / 2) {
      triggerWrite(SCAN_TRIGGER_OUTPUT, HIGH);
    }
    if (output_scan_index < SCAN_STEPS - 1) {
      output_scan_index++;
    }
    else {
      output_scan_index = 0;
    }
  }
  else if (feedback_on) {
    float error = current_error - error_offset;
    float proportional = p_gain * error;
    integral = new_integral(integral, p_gain * ERROR_ADC_INTERVAL / i_time * error);
    float differential = 0.0;
    if (previous_error > -99.0) {  // not the first data point.
      differential = p_gain * d_time / ERROR_ADC_INTERVAL * (current_error - previous_error);
    }
    previous_error = error + error_offset;

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

void cmd_error_offset(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    error_offset = atof(qC.current());
    writeDAC(LASER_JUMP_OUTPUT, -error_offset);
  }
  S.printf("error offset is %f\n", error_offset);
}

void cmd_output_offset(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    output_offset = atof(qC.current());
  }
  S.printf("output offset is %f\n", output_offset);
}

void cmd_output_scan(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    output_scan = atof(qC.current());
  }
  S.printf("output scan is %f\n", output_scan);
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

void cmd_state(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    state = atoi(qC.current());
  }
  if (state == 0) {
    integral = 0.0;
    previous_error = -100.0;
    output_scan_index = 0;
    error_index = 0;
    output_index = 0;

    triggerWrite(SCAN_TRIGGER_OUTPUT, LOW);
    triggerWrite(LOCK_TRIGGER_OUTPUT, HIGH);
  }
  else {
    writeDAC(CONTROL_OUTPUT, output_offset);
    triggerWrite(SCAN_TRIGGER_OUTPUT, LOW);
    triggerWrite(LOCK_TRIGGER_OUTPUT, LOW);
  }
  S.printf("state is %i\n", state);
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

void cmd_error_data(qCommand& qC, Stream& S){
  pause_error_data = true; // pause data taking during process
  int get_data_length = MAX_DATA_LENGTH;
  if ( qC.next() != NULL) {
    get_data_length = atoi(qC.current());
  }
  serial_print_data(S, error_data, error_index, get_data_length);
  pause_error_data = false;
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
  qC.addCommand("error_offset", cmd_error_offset);
  qC.addCommand("output_offset", cmd_output_offset);
  qC.addCommand("output_scan", cmd_output_scan);
  qC.addCommand("output_lower_limit", cmd_output_lower_limit);
  qC.addCommand("output_upper_limit", cmd_output_upper_limit);
  qC.addCommand("state", cmd_state);
  qC.addCommand("error_data", cmd_error_data);
  qC.addCommand("output_data", cmd_output_data);
  qC.addCommand("limit_warnings", cmd_limit_warnings);
  qC.addCommand("integral", cmd_integral);
  configureADC(ERROR_INPUT, ERROR_ADC_INTERVAL, ADC_DELAY, ERROR_ADC_SCALE, error_adc_loop);
  configureADC(WAVEMETER_INPUT, WAVEMETER_ADC_INTERVAL, ADC_DELAY, WAVEMETER_ADC_SCALE, wavemeter_adc_loop);
  triggerMode(SCAN_TRIGGER_OUTPUT, OUTPUT);
  triggerMode(LOCK_TRIGGER_OUTPUT, OUTPUT);
  triggerWrite(LOCK_TRIGGER_OUTPUT, HIGH);
  writeDAC(LASER_JUMP_OUTPUT, -error_offset);
}

void loop(){
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
}
