/**
 * Quarto code for laser piezo control.
 * It is designed to work with the Vescent D2-125 servo which provides fast
 * but small-range feedback to the laser (current or AOM).
 * The output monitor from the Vescent goes into the Quarto error input,
 * and Quarto adjusts the piezo to provide slow feedback to keep the error input stable.
 * The Quarto lock trigger output should be connected to relative jump TTL input of the Vescent.
 *
 * The quarto has three states:
 * State 0: Quarto output offset and scan can be changed. The lock trigger
 * output is high (unlocked) in this state.
 * State 1: Quarto stops scanning, and changes the lock trigger output to
 * low (locked). It also provides PID feedback to the output offset
 * to keep error input at the last reading in state 0.
 * State 2: Detects unlock using the transmission voltage. Attempts to relock using the last known
 * good Quarto output voltage.
*/

#include "qCommand.h"
#include <math.h>
qCommand qC;

// error signal analog input port
const uint8_t ERROR_INPUT = 1;
// cavity transmission signal analog input port
const uint8_t TRANSMISSION_INPUT = 2;
// cavity error signal analog input port
const uint8_t CAVITY_ERROR_INPUT = 3;
// control signal analog output port
const uint8_t CONTROL_OUTPUT = 1;
// laser jump amplitude analog output port
const uint8_t LASER_JUMP_OUTPUT = 2;
// scan signal TTL trigger port
const uint8_t SCAN_TRIGGER_OUTPUT = 1;
// lock engage signal TTL output port
const uint8_t LOCK_TRIGGER_OUTPUT = 2;

// interval in us for ADC data reading
const uint16_t ADC_INTERVAL = 10;  // related to the scan time in state 0.
const uint16_t ADC_DELAY = 0;
const adc_scale_t ERROR_ADC_SCALE = BIPOLAR_10V;
const adc_scale_t TRANSMISSION_ADC_SCALE = BIPOLAR_2500mV;
const adc_scale_t CAVITY_ERROR_ADC_SCALE = BIPOLAR_10V;

// scan steps (SCAN_STEPS * ADC_INTERVAL = scan time)
const int SCAN_STEPS = 1000;

// PID parameters for piezo feedback to the error signal
float p_gain = 0.001;
float i_time = 1000.0;  // us
float d_time = 0.0;  // us

// error signal offset
float laser_jump_offset = -6.0;
// error signal offset
float error_offset = 5.468;
// keeps track of the integral term
float integral = 0.0;
// limits the integral term magnitude so it does not blow up
float integral_limit = 2.0;
float current_error = 0.0;
// last error signal for D gain.
float previous_error = -100.0;

// output voltage offset
float output_offset = 5.0;
// output voltage scan
float output_scan = 0.3;
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

// auto relock parameters
float last_good_integral = 0.0;
float transmission_unlock_voltage = 0.005;
const int SAMPLES_CONFIRM_UNLOCK = 10;
int confirm_unlock_index = -1;
const int SAMPLES_WAIT_LOCK = 50;
int wait_lock_index = -1;

// Data saved in Quarto for computer readout
const int MAX_DATA_LENGTH = SCAN_STEPS * 2;
const int SYNC_DATA_LENGTH = SCAN_STEPS;
float error_data[MAX_DATA_LENGTH];
float output_data[MAX_DATA_LENGTH];
float cavity_error_data[MAX_DATA_LENGTH];
float transmission_data[MAX_DATA_LENGTH];
int data_index = 0;
bool pause_data = false;


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
  bool local_pause_data = pause_data;
  if (!local_pause_data) {
    error_data[data_index] = current_error;
  }
  update_pid(local_pause_data);  // this function must be fast compared to the ADC sample interval.
  if (!local_pause_data) {
    if (data_index < MAX_DATA_LENGTH - 1) {
      data_index++;
    }
    else {
      data_index = 0;
    }
  }
}

void cavity_error_adc_loop(void) {
  float cavity_error;
  switch (CAVITY_ERROR_INPUT) {
    case 1:
      cavity_error = readADC1_from_ISR();
      break;
    case 2:
      cavity_error = readADC2_from_ISR();
      break;
    case 3:
      cavity_error = readADC3_from_ISR();
      break;
    case 4:
      cavity_error = readADC4_from_ISR();
      break;
  }
  if (!pause_data) {
    cavity_error_data[data_index] = cavity_error;
  }
}

void transmission_adc_loop(void) {
  float transmission;
  switch (TRANSMISSION_INPUT) {
    case 1:
      transmission = readADC1_from_ISR();
      break;
    case 2:
      transmission = readADC2_from_ISR();
      break;
    case 3:
      transmission = readADC3_from_ISR();
      break;
    case 4:
      transmission = readADC4_from_ISR();
      break;
  }
  if (!pause_data) {
    transmission_data[data_index] = transmission;
  }
  if (state > 0) {
    if (wait_lock_index < 0) {
      if (transmission > transmission_unlock_voltage) {
        last_good_integral = integral;
        confirm_unlock_index = -1;
      }
      else if (confirm_unlock_index < 0) {
        confirm_unlock_index = SAMPLES_CONFIRM_UNLOCK - 1;
      }
      else if (confirm_unlock_index > 0) {
        confirm_unlock_index -= 1;
      }
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

void update_pid(bool local_pause_data) {
  bool scan_on = false;
  bool feedback_on = false;
  bool auto_relock_on = false;
  switch (state) {
    case 0:  // feedback off
      integral = 0.0;
      previous_error = -100.0;
      scan_on = true;
      break;
    case 1:  // feedback on
      feedback_on = true;
      break;
    case 2:  // feedback on, auto relock on
      feedback_on = true;
      auto_relock_on = true;
      break;
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
  if (auto_relock_on) {
    if (confirm_unlock_index == 0) {
      feedback_on = false;
      wait_lock_index = 2 * SAMPLES_WAIT_LOCK - 1;
      output = output_offset + last_good_integral;
      confirm_unlock_index = -1;
      triggerWrite(LOCK_TRIGGER_OUTPUT, HIGH);
    }
    else if (wait_lock_index >= 0) {
      feedback_on = false;
      wait_lock_index -= 1;
      output = output_offset + last_good_integral;
      if (wait_lock_index == SAMPLES_WAIT_LOCK) {
        triggerWrite(LOCK_TRIGGER_OUTPUT, LOW);
      }
    }
  }
  if (feedback_on) {
    float error = current_error - error_offset;
    float proportional = p_gain * error;
    integral = new_integral(integral, p_gain * ADC_INTERVAL / i_time * error);
    float differential = 0.0;
    if (previous_error > -99.0) {  // not the first data point.
      differential = p_gain * d_time / ADC_INTERVAL * (current_error - previous_error);
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

  if (!local_pause_data) {
    output_data[data_index] = output;
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
  }
  S.printf("error offset is %f\n", error_offset);
}

void cmd_laser_jump_offset(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    laser_jump_offset = atof(qC.current());
    writeDAC(LASER_JUMP_OUTPUT, laser_jump_offset);
  }
  S.printf("laser jump offset is %f\n", laser_jump_offset);
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

void cmd_transmission_unlock(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    transmission_unlock_voltage = atof(qC.current());
  }
  S.printf("transmission unlock is %f\n", transmission_unlock_voltage);
}

void cmd_integral(qCommand& qC, Stream& S){
  S.printf("integral term is %f\n", integral);
}

void cmd_state(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    int new_state = atoi(qC.current());
    if (new_state <= 2) {
      state = new_state;
      if (state == 0) {
        integral = 0.0;
        previous_error = -100.0;
        output_scan_index = 0;
        data_index = 0;
        wait_lock_index = -1;
        confirm_unlock_index = -1;
        triggerWrite(SCAN_TRIGGER_OUTPUT, LOW);
        triggerWrite(LOCK_TRIGGER_OUTPUT, HIGH);
      }
      else {
        triggerWrite(SCAN_TRIGGER_OUTPUT, LOW);
        triggerWrite(LOCK_TRIGGER_OUTPUT, LOW);
      }
    }
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
  pause_data = true; // pause data taking during process
  int get_data_length = MAX_DATA_LENGTH;
  if ( qC.next() != NULL) {
    get_data_length = atoi(qC.current());
  }
  serial_print_data(S, error_data, data_index, get_data_length);
  pause_data = false;
}

void cmd_output_data(qCommand& qC, Stream& S){
  pause_data = true; // pause data taking during process
  int get_data_length = MAX_DATA_LENGTH;
  if ( qC.next() != NULL) {
    get_data_length = atoi(qC.current());
  }
  serial_print_data(S, output_data, data_index, get_data_length);
  pause_data = false;
}

void cmd_all_data(qCommand& qC, Stream& S){
  pause_data = true; // pause data taking during process
  int start_index = SYNC_DATA_LENGTH;
  if (data_index > SYNC_DATA_LENGTH) {
    start_index = 0;
  }
  int end_index = start_index + SYNC_DATA_LENGTH;
  for (int i = start_index; i < end_index; i++) {
    S.printf("%f\n", error_data[i]);
  }
  for (int i = start_index; i < end_index; i++) {
    S.printf("%f\n", output_data[i]);
  }
  for (int i = start_index; i < end_index; i++) {
    S.printf("%f\n", transmission_data[i]);
  }
  for (int i = start_index; i < end_index; i++) {
    S.printf("%f\n", cavity_error_data[i]);
  }
  output_scan_index = 0;
  data_index = 0;
  pause_data = false;
}

void cmd_last_transmission_point(qCommand& qC, Stream& S){
  S.printf("Last transmission point is %f\n", transmission_data[data_index]);
}

void cmd_last_output_point(qCommand& qC, Stream& S){
  S.printf("Last output was %f\n", output_data[data_index]);
}

void cmd_limit_warnings(qCommand& qC, Stream& S) {
  float output = output_data[data_index];

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
  qC.addCommand("laser_jump_offset", cmd_laser_jump_offset);
  qC.addCommand("output_offset", cmd_output_offset);
  qC.addCommand("output_scan", cmd_output_scan);
  qC.addCommand("output_lower_limit", cmd_output_lower_limit);
  qC.addCommand("output_upper_limit", cmd_output_upper_limit);
  qC.addCommand("transmission_unlock", cmd_transmission_unlock);
  qC.addCommand("state", cmd_state);
  qC.addCommand("error_data", cmd_error_data);
  qC.addCommand("output_data", cmd_output_data);
  qC.addCommand("all_data", cmd_all_data);
  qC.addCommand("limit_warnings", cmd_limit_warnings);
  qC.addCommand("integral", cmd_integral);
  qC.addCommand("last_transmission_point", cmd_last_transmission_point);
  qC.addCommand("last_output_point", cmd_last_output_point);
  configureADC(ERROR_INPUT, ADC_INTERVAL, ADC_DELAY, ERROR_ADC_SCALE, error_adc_loop);
  configureADC(TRANSMISSION_INPUT, ADC_INTERVAL, ADC_DELAY, TRANSMISSION_ADC_SCALE, transmission_adc_loop);
  configureADC(CAVITY_ERROR_INPUT, ADC_INTERVAL, ADC_DELAY, CAVITY_ERROR_ADC_SCALE, cavity_error_adc_loop);
  triggerMode(SCAN_TRIGGER_OUTPUT, OUTPUT);
  triggerMode(LOCK_TRIGGER_OUTPUT, OUTPUT);
  triggerWrite(LOCK_TRIGGER_OUTPUT, HIGH);
  writeDAC(LASER_JUMP_OUTPUT, laser_jump_offset);
}

void loop(){
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
}
