/* See {muff_utils.h}. */
/* Created by Gustavo Lelis (UFF) and Jorge Stolfi (UNICAMP), 2017-2018. */
/* Last edited on 2018-12-17 14:22:37 by stolfilocal */

#include "Arduino.h"
#include <AccelStepper.h>
#include <muff_utils.h>
#include <muff_comandos.h>

void comando_aciona_motor(AccelStepper *motor, int desloc, int max_vel, bool completa)
  {
    // Se o motor estiver em movimento, interrompe:
    para_motor(motor);
    
    // Notifica quem chamou
    Serial.print("# Girando o motor no sentido ");
    if (desloc > 0)
      { Serial.print("horario"); }
    else
      { Serial.print("anti-horario"); }
    Serial.print(" por ");
    Serial.print(desloc);
    Serial.print(" passos, vel max ");
    Serial.print(max_vel);
    Serial.println(" passos/seg");
    
    aciona_motor(motor, desloc, max_vel);
    
    if (completa)
      { // Gera passos ateh o motor chegar no ponto desejado e parar:
        while (motor->isRunning()) { motor->run(); } 
        motor->disableOutputs();
      }
  }
    
void comando_para_motor(AccelStepper *motor)
  {
    if (motor->isRunning()) 
      { Serial.println("# Parando o motor...");
        para_motor(motor);
      }
  }

void comando_define_desloc_quadro(int *desloc)
  { 
    Serial.println("# Definindo o deslocamento padrao entre quadros");
    // Recebe o argumento
    char arg[5]; // Quatro bytes do argumento e um '\0' para terminar a cadeia.
    bool ok = true;
    for (int k = 0; k < 4; k++)
      { while (Serial.available() <= 0) { }
        arg[k] = Serial.read();
        if (k == 0)
          { ok &= ((arg[k] == '+') || (arg[k] == '-')); }
        else
          { ok &= ((arg[k] >= '0') && (arg[k] <= '9')); }
      }
    arg[4] = '\0'; // Marca fim da cadeia.
    Serial.print("# Argumento = ");
    Serial.print(arg);
    Serial.print(" microns");
    
    if (! ok)
      { Serial.println("");
        muff_erro("valor invalido");
      }
    else
      { // Converte os 4 caracters para inteiro em -999 a +999 (microns):
        int microns = (arg[1] - '0')*100 + (arg[2] - '0')*10 + (arg[3] - '0');

        // Converte o valor em microns para numero de passos do motor:
        int npp = nanometros_por_passo;
        int passos = (microns*((long int)1000)+(npp/2))/npp;
        if (arg[0] == '-') { passos = - passos;  microns = - microns; }

        // Informa usuario sobre conversao: 
        Serial.print(" = ");
        Serial.print(passos);
        Serial.println(" passos");
        (*desloc) = passos;
      }
  }
  
void comando_define_max_acel(int *max_acel)
  { 
    Serial.println("# Definindo a aceleracao maxima");
    // Recebe o argumento
    char arg[4]; // Tres bytes do argumento e um '\0' para terminar a cadeia.
    bool ok = true;
    for (int k = 0; k < 3; k++)
      { while (Serial.available() <= 0) { }
        arg[k] = Serial.read();
        ok &= ((arg[k] >= '0') && (arg[k] <= '9'));
      }
    arg[4] = '\0'; // Marca fim da cadeia.
    Serial.print("# Argumento = ");
    Serial.print(arg);
    if (! ok) 
      { Serial.println("");
        muff_erro("valor invalido - deve ser '000' a '999'");
      }
    else
      { // Converte os 3 caracters para inteiro em 000 a 999:
        int acel = (arg[0] - '0')*100 + (arg[1] - '0')*10 + (arg[2] - '0');
        Serial.print(" = ");
        Serial.print(acel);
        Serial.print(" passos/seg^2");
        Serial.println(""); 
        
        if (acel == 0) { muff_erro("aceleracao maxima nao pode ser nula"); }
    
        (*max_acel) = acel;
      }
  }

void comando_aciona_leds(int estado, int estados_dos_leds[])
  { 
    if (estado == 1)
      { Serial.println("# Ligando LED(s)"); }
    else
      { Serial.println("# Desligando LED(s)"); }
      
    // Recebe o caracter que identifica o(s) LED(s):
    while (Serial.available() <= 0) { }
    int cod_led = Serial.read();
    mostra_byte("codigo do(s) LED(s)", cod_led);

    if (cod_led == '@')
      { aciona_todos_os_leds(estado, estados_dos_leds); }
    else 
      { int indice_led = cod_led - 'A'; // Numero do led, 0 a nLED-1.
        if ((indice_led < 0) || (indice_led >= num_leds))
          { muff_erro("codigo de LED invalido"); }
        else
          { aciona_um_led(indice_led, estado, estados_dos_leds); }
      }
  }

void mostra_byte(char *mensagem, int byte)
  { 
    Serial.print("# ");
    Serial.print(mensagem);
    Serial.print(" = '");
    Serial.print((char)(byte & 255));
    Serial.print("' = chr(");
    Serial.print((int)byte);
    Serial.println(")");
  }
 
void mostra_comando(int comando)
  { 
    mostra_byte("Comando recebido", comando);
  }
        
