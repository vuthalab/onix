#include "qCommand.h"
#include <math.h>
qCommand qC;


float sample_rate = 10; // us
float dt = 1; //pow(sample_rate, -6); // in us
float i_time = 900.0; // integral time in us
float d_time = 20; // derivative time in us
float p_gain = 0.02; // proportional gain
float integral = 0.0; // accumulated integral error
float SETPOINT = 1.6; // setpoint
float offset = 0.0; // output offsetci
float previous_error = 0.0;
float difference = 0.0;
float out = 0.0;
float upperLimit = 10.0;
float integratorLimit = 10.0;

bool pid = false;

int numStore = 100;
int16_t errorData[100];
int16_t outputData[100];
int dataIndex = 0;



void PIDloop(void){
  int16_t newadc = readADC1RAW_from_ISR();

  if (pid) {
    float newadc_V = 1.5625 * pow(10,-4) * newadc - SETPOINT;
    float integral_increment = p_gain*(1/i_time)*newadc_V*dt;
    integral += integral_increment;
    difference = newadc_V - previous_error;
    previous_error = newadc_V;
    
    float prop = newadc_V* p_gain;

    if ((integral > integratorLimit) || (integral < -integratorLimit)) {
      integral -= integral_increment;
    }

    out = prop + integral + p_gain*(d_time/dt)*difference + offset;

    if (out < 0) {
      out = 0;
    }

    if (out > upperLimit) {
      out = upperLimit;
    }

    errorData[dataIndex] = int(newadc_V * 1e3);

    int16_t out_int = out / (1.5625 * pow(10,-4));
    outputData[dataIndex] = out_int;

    dataIndex++;
    if (dataIndex == numStore){
      dataIndex = 0;
    }
    
    writeDAC(1, out);
    writeDAC(2, out);
    writeDAC(3, newadc_V);
  }
}

void GeterrorData(qCommand& qC, Stream& S){
  for (int i = 0; i < numStore; i++){
    S.println(errorData[i]);
  }
}

void GetoutputData(qCommand& qC, Stream& S){
  for (int i = 0; i < numStore; i++){
    S.println(outputData[i]);
  }
}


void c(qCommand& qC, Stream& S){
  integral = 0;
  S.printf("Integral term reset\n");
}

void p(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    p_gain = atof(qC.current());
  }
  S.printf("p gain is %f\n", p_gain);
}


void i(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    i_time = atof(qC.current());
  }
  S.printf("i time is %f\n", i_time);
}

void d(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    d_time = atof(qC.current());
  }
  S.printf("d time is %f\n", d_time);
}

void s(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    SETPOINT = atof(qC.current());
  }
  S.printf("Setpoint is %f\n", SETPOINT);
}

void u(qCommand& qC, Stream& S){
  if ( qC.next() != NULL) {
    upperLimit = atof(qC.current());
  }
  S.printf("Upper Limit is %f\n", upperLimit);
}

void o(qCommand& qC, Stream& S){
   if ( qC.next() != NULL) {
    offset = atof(qC.current());
   }
   S.printf("offset is %f\n", offset);
}

void state(qCommand& qC, Stream& S){  // int -> bool conversion is incorrect
   if ( qC.next() != NULL) {
    if (atoi(qC.current())){
      pid = true;
      integral = 0;
      S.printf("state is %i\n", 0);
    }
    else {
      pid = false;
      S.printf("state is %i\n", 1);
    }
   }
}

void setup(void) {
  configureADC(1, sample_rate, 0, BIPOLAR_10V, PIDloop);
  qC.addCommand("p", p);
  qC.addCommand("i", i);
  qC.addCommand("d", d);
  qC.addCommand("c", c);
  qC.addCommand("s", s);
  qC.addCommand("u", u);
  qC.addCommand("o", o);
  qC.addCommand("edata", GeterrorData);
  qC.addCommand("odata", GetoutputData);
  qC.addCommand("state", state);
}

void loop(){
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
}
