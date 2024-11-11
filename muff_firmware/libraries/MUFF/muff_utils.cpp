/* See {muff_utils.h}. */
/* Created by Gustavo Lelis (UFF) and Jorge Stolfi (UNICAMP), 2017-2018. */
/* Last edited on 2018-09-04 18:51:48 by stolfilocal */

#include "Arduino.h"
#include <AccelStepper.h>
#include <muff_utils.h>

// -----------------------------------------------------------
// UTILITARIOS PARA COMUNICACAO

#define bauds_serial (9600)
  // Velocidade da porta serial.

void inicializa_porta_serial(void)
  {
    Serial.begin(bauds_serial);
    Serial.println("# Teste 123....");
  }

void muff_erro(char *mensagem)
  { Serial.print("# ** ");
    Serial.println(mensagem);
  }

// -----------------------------------------------------------
// UTILITARIOS PARA ACIONAMENTO DO MOTOR

#define motor1_interfaceType (AccelStepper::DRIVER)
  // Tipo de interface do motor de passo (2 pinos: "step" e "direction").
  
#define motor1_stepPin (3)                          
  // Numero do pino "step".
  
#define motor1_dirPin (4)                           
  // Numero do pino "direction".
  
#define motor1_disablePin (2)                        
  // Numero do pino "enable".

AccelStepper inicializa_motor1(int max_acel)
  { 
    // Cria o registro de configuracao e estado:
    AccelStepper motor1(motor1_interfaceType, motor1_stepPin, motor1_dirPin);
    
    // Define o pino "disable" do motor:
    pinMode(motor1_disablePin, OUTPUT);
    motor1.setEnablePin(motor1_disablePin);
    motor1.setPinsInverted(0,0,1);
    
    // Parametros e estado inicial:
    motor1.disableOutputs();
    motor1.setAcceleration(max_acel);
    motor1.setCurrentPosition(0);
    motor1.moveTo(0);  // Objetivo eh ficar onde estah.
    motor1.enableOutputs();
    
    return motor1;
  }

void aciona_motor(AccelStepper *motor, int desloc, int max_vel)
  {
    // Para o motor, se estiver em movimento:
    para_motor(motor);
    
    motor->disableOutputs();
    motor->setMaxSpeed(max_vel);
    motor->setCurrentPosition(0);
    motor->moveTo(desloc);
    motor->enableOutputs();
    // Serial.print('>'); Serial.print(motor->distanceToGo());
    // if (motor->isRunning()) { Serial.print('$'); } else { Serial.print('*'); }
  } 
  
void para_motor(AccelStepper *motor)
  {
    if (motor->isRunning()) 
      { // Define o objetivo do motor como sendo "parar o mais cedo possivel":
        motor->stop();
        // Espera o motor parar: 
        while (motor->isRunning()) { motor->run(); }
        motor->disableOutputs();
      }
  }

// -----------------------------------------------------------
// UTILITARIOS PARA ACIONAMENTO DOS LEDS

#define leds_latchPin (8)
#define leds_clockPin (9)
#define leds_dataPin (6)

void inicializa_leds(int estados_dos_leds[])
  { 
    // Inicializa o estado dos pinos do multiplexador:
    pinMode(leds_latchPin, OUTPUT);
    pinMode(leds_clockPin, OUTPUT);
    pinMode(leds_dataPin, OUTPUT); 
    
    // Garante e lembra que todos os LEDs est�o apagados:
    aciona_todos_os_leds(0,estados_dos_leds);
  }

void atualiza_leds(int estados_dos_leds[])
  // (Re)envia o vetor {estados_dos_leds[0..2]} para o multiplexador.
  {
    digitalWrite(leds_latchPin, LOW);
    shiftOut(leds_dataPin, leds_clockPin, LSBFIRST, estados_dos_leds[0]);
    shiftOut(leds_dataPin, leds_clockPin, LSBFIRST, estados_dos_leds[1]);
    shiftOut(leds_dataPin, leds_clockPin, LSBFIRST, estados_dos_leds[2]);
    digitalWrite(leds_latchPin, HIGH);
  }

void aciona_um_led(int indice_led, int estado, int estados_dos_leds[])
  { 
    int grupo = indice_led / 8; // Indice do grupo de 8 LEDs (0 a 2).
    int indice_bit = (indice_led + 7) % 8;  // Indice do bit no grupo (0 a 7).
    int mascara = (1 << indice_bit); // Mascara do bit.
    if (estado == 1)
      { // Liga o bit:
        estados_dos_leds[grupo] |= mascara;
      }
    else if (estado == 0)
      { // Desliga o bit: 
        estados_dos_leds[grupo] &= (0b11111111 ^ mascara);
      }
    atualiza_leds(estados_dos_leds);
  }
    
void aciona_todos_os_leds(int estado, int estados_dos_leds[])
  { 
    for (int grupo = 0; grupo < 3; grupo++)
      { if (estado == 1)
          { // Liga todos os 8 bits:
            estados_dos_leds[grupo] = 0b11111111;
          }
        else if (estado == 0)
          { // Desliga todos os 8 bits: 
            estados_dos_leds[grupo] = 0b00000000;
          }
      }
    atualiza_leds(estados_dos_leds);
  }
