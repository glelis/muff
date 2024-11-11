/* Utility functions for the MUFF v2.0 microscope positioner firmware. */
/* Created by Gustavo Lelis (UFF) and Jorge Stolfi (UNICAMP), 2017-2018. */
/* Last edited on 2018-09-04 18:21:41 by stolfilocal */

#ifndef muff_utils_H
#define muff_utils_H

// -----------------------------------------------------------
// UTILITARIOS PARA COMUNICACAO

void inicializa_porta_serial(void);
  // Inicializa a porta serial com a velocidade certa
  // e escreve nela uma mensagem de teste.

void muff_erro(char *mensagem);
  // Escreve na porta serial uma linha "# ** {mensagem}".
  // NAO termina o programa.

// -----------------------------------------------------------
// UTILITARIOS PARA ACIONAMENTO DOS LEDS

#define num_leds 24
  // Numero de LEDs no posicionador.
  
#define num_bytes_leds (((num_leds) + 7)/8)
  // Numero de bytes no vetor de estados dos LEDs.
  
// As funcoes abaixo usam e modificam o vetor de inteiros 
// {estados_dos_leds[0..num_bytes_leds-1]} cujos bits descrevem
// os estados correntes dos LEDs (0 = desligado, 1 = ligado).
// Cada elemento do vetor contem os estados de 8 LEDs.

void inicializa_leds(int estados_dos_leds[]);
  // Inicializa os pinos de controle do multiplexador de 
  // LEDs para saida.  Inicializa todos os LEDs
  // para "apagado".
  
void aciona_um_led(int indice_led, int estado, int estados_dos_leds[]);
  // Aciona o LED de indice {indice_led} (de 0 a {num_leds-1}) 
  // para o {estado} indicado (0 = desligado, 1 = ligado).

void aciona_todos_os_leds(int estado, int estados_dos_leds[]);
  // Aciona todos os LEDs para o {estado} indicado (0 = desligado, 1 = ligado).
  
// -----------------------------------------------------------
// UTILITARIOS PARA ACIONAMENTO DO MOTOR
  
#define nanometros_por_passo (6250)   
  // Deslocamento do carro por passo do motor principal (nm).

AccelStepper inicializa_motor1(int maxAcel);
  // Cria um objeto do tipo {AccelStepper} que vai representar
  // a configuracao e estado do motor de passo 1 (principal,
  // que move a camera verticalmente).
  // 
  // Define a aceleracao maxima {maxAcel} (passos/segundo^2).
  // Inicializa o estado como "parado".
  //
  // Esta funcao supoe que os pinos 3 e 4 do Arduino sao
  // "step" e "direction" do motor 1, e que o pino 2 significa 
  // "enable" quando {LOW}, "disable" quando {HIGH}.

void aciona_motor(AccelStepper *motor, int desloc, int max_vel);
  // Define o objetivo do motor como sendo
  // mover {desloc} passos a partir da posicao corrente,
  // e executa {motor.enableOutputs()}. 
  // 
  // Define tambem a velocidade maxima {maxVel} (passos/segundo)
  // permitida durante esse movimento.
  
  // Esta funcao deve ser chamada retorna imediatamente.  Quem chamou
  // deve usar {motor.run()} para efetuar o movimento,
  // ateh {motor.isRunning()} retornar falso, e 
  // entao executar {motor.disableOutputs()}.
  
void para_motor(AccelStepper *motor);
  // Interrompe o movimento do motor, se estiver em 
  // movimento.  Retorna apenas quando estiver parado.

#endif
