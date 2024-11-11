/* Arduino firmware for the automatic MUFF v2.0 microscope positioner. */
/* Created by Gustavo Lelis (UFF) and Jorge Stolfi (UNICAMP), 2017-2018. */
/* Last edited on 2019-01-07 18:54:47 by stolfilocal */

#include <AccelStepper.h>
#include <muff_utils.h>
#include <muff_comandos.h>

// Estado interno do firmware:

int estados_dos_leds[num_bytes_leds]; // Bytes cujos bits indicam os estados correntes dos LEDs.

// Parametros do motor de passo principal (a ajustar experimentalmente):

int motor1_max_acel = 500;   // Aceleracao maxima (passos/segundo^2).

int desloc_ajuste_fino = 30;       // Passos a deslocar nos comandos '1', '2'. 
int motor1_max_vel_fino = 80;      // Velocidade maxima no ajuste fino (passos/segundo).

int desloc_ajuste_grosso = 15000;  // Passos a deslocar nos comandos '6', e '7'. 
int motor1_max_vel_grosso = 400;   // Velocidade maxima no ajuste grosseiro (passos/segundo).

int desloc_quadro = 0;             // Passos a deslocar no comando '5', definido pelo comando '4'.
int motor1_max_vel_quadro = 400;   // Velocidade maxima do comando '5' (passos/segundo).

const int pinoChave = 10; //PINO DIGITAL UTILIZADO PELA CHAVE FIM DE CURSO

AccelStepper motor1; // Configuracao e estado do motor.

void setup()
  { inicializa_porta_serial();
  
    inicializa_leds(estados_dos_leds);
    
    motor1 = inicializa_motor1(motor1_max_acel);

    pinMode(pinoChave, INPUT_PULLUP); //DEFINE O PINO COMO ENTRADA / "_PULLUP" É PARA ATIVAR O RESISTOR INTERNO DO ARDUINO PARA GARANTIR QUE NÃO EXISTA FLUTUAÇÃO ENTRE 0 (LOW) E 1 (HIGH)

    // Prompt em caso de interacao direta com usuario
    Serial.println("# Digite comando ('1', '2', etc) e clique em ENVIAR...");
  }

void processa_comando(int comando)
  {
    mostra_comando(comando);
    if (comando == '1')
      { comando_aciona_motor(&motor1, +desloc_ajuste_fino, motor1_max_vel_fino, 0); }
    else if (comando == '2')
      { comando_aciona_motor(&motor1, -desloc_ajuste_fino, motor1_max_vel_fino, 0); }
    else if (comando == '3')
      { comando_para_motor(&motor1); }
    else if (comando == '4')
      { comando_define_desloc_quadro(&desloc_quadro); }
    else if (comando == '5')
      { comando_aciona_motor(&motor1, desloc_quadro, motor1_max_vel_quadro, 1); }
    else if (comando == '+')
      { comando_aciona_leds(1,estados_dos_leds); }
    else if (comando == '-')
      { comando_aciona_leds(0,estados_dos_leds); }
    else if (comando == '6')
      { comando_aciona_motor(&motor1, +desloc_ajuste_grosso, motor1_max_vel_grosso, 0); }
    else if (comando == '7')
      { comando_aciona_motor(&motor1, -desloc_ajuste_grosso, motor1_max_vel_grosso, 0); }
    else if (comando == '8')
      { comando_define_max_acel(&motor1_max_acel); }
    else
      { muff_erro("comando invalido");  }

    // Notifica o usuario de que ocomando foi executado:
    Serial.print('0');
  }

void loop(void)
  // Loop principal do firmware. 
  { // Gera pulsos para o motor se e como necessario:
    if (motor1.isRunning())
      { // Motor estah em movimento:
        // Serial.print('!'); Serial.print(motor1.distanceToGo());
        motor1.run();
      }
    else
      { // Motor estah parado, desligue alimentacao para poupar energia:
        motor1.disableOutputs();
      }
    // Verifica se ha comando:
    if (Serial.available() > 0) 
      { // Chegou um comando:
        int comando = Serial.read();
        processa_comando(comando);
      }

    // Para o motor em caso de acionamento do sensor fim de curso
    if(digitalRead(pinoChave) == LOW)
      { //SE A LEITURA DO PINO FOR IGUAL A LOW, FAZ
        processa_comando('2');
        delay(1000);
        processa_comando('3');
      }
  }
      
