// Quarto code for dividing a input clock

#include "qCommand.h"
#include <math.h>
qCommand qC;

const uint8_t TRIGGER_INPUT_PORT = 1;
int decimation_ratio = 42;
int current_step = 0;

void triggered(void) {
  current_step += 1;
  if (current_step >= decimation_ratio / 2) {
    writeDAC(1, 5);
  }
  if (current_step >= decimation_ratio) {
    current_step = 0;
    writeDAC(1, 0);
  }
}

void cmd_decimation_ratio(qCommand& qC, Stream& S) {
  if ( qC.next() != NULL) {
    decimation_ratio = atoi(qC.current());
  }
  S.printf("decimation ratio is %i\n", decimation_ratio);
}

void setup(void) {
  qC.addCommand("decimation_ratio", cmd_decimation_ratio);
  triggerMode(TRIGGER_INPUT_PORT, INPUT);
  enableInterruptTrigger(TRIGGER_INPUT_PORT, RISING_EDGE, triggered);
}

void loop(){
  qC.readSerial(Serial);
  qC.readSerial(Serial2);
}
