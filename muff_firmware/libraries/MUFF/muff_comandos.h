/* Command-processing functions for the MUFF v2.0 microscope positioner firmware. */
/* Created by Gustavo Lelis (UFF) and Jorge Stolfi (UNICAMP), 2017-2018. */
/* Last edited on 2018-12-17 14:15:00 by stolfilocal */

#ifndef muff_comandos_H
#define muff_comandos_H

#include <AccelStepper.h>
#include <muff_utils.h>

void comando_aciona_motor(AccelStepper *motor, int desloc, int maxVel, bool completa);
  // Inicia o movimento do {motor} {desloc} passos a partir da posicao
  // corrente, com velocidade maxima {maxVel}. O valor {desloc} pode ser 
  // positivo (horario,sobe) ou negativo (antihorario,desce).
  // O valor de {maxVel} deve ser sempre positivo.
  // 
  // Se {completa} eh true, executa {motor.run} internamente 
  // e somente retorna quando o movimento tiver terminado
  // e o motor estiver parado.
  // 
  // Se {completa} eh false, apenas inicia o movimento e retorna
  // imediatamente, sem esperar terminar. O loop principal deve chamar
  // {motor.run()} repetidamente para realmente executar o movimento,
  // enquanto {motor.isRunning()} for verdade. O movimento pode ser
  // interrompido por uma chamada de {comando_para_motor} ou outra
  // chamada desta funcao.
  //
  // Se o motor ja estiver em movimento, interrompe o mesmo antes de iniciar.  

void comando_para_motor(AccelStepper *motor);
  // Interrompe o movimento do {motor}, se estiver em movimento, na posicao
  // corrente.
  // 
  // Somente retorna quando o motor estiver parado.
  // Se o motor jah estiver parado, nao faz nada.

void comando_define_desloc_quadro(int *desloc);
  // Define a distancia a deslocar para {comando_executa_desloc_quadro}.
  // O codigo de comando deve ser seguido de 4 bytes -- um sinal e 3
  // digitos decimais -- especificando um valor em microns. Converte
  // esse valor de microns para passos do motor, e guarda em {*desloc}.
  //
  // Este comando nao depende do estado do motor de passo e 
  // nao afeta o movimento do mesmo.

void comando_define_max_acel(int *max_acel);
  // Define a aceleracao maxima {max_acel} de um motor de passo.
  // O codigo de comando deve ser seguido de 3
  // digitos decimais, especificando a aceleracao maxima em passos / segundo^2.
  // Converte esse valor para binário e aguarda em {*desloc}.
  //
  // Se o motor de passo estiver em movimento, este comando so vai
  // ter efeito no proximo movimento.

void comando_aciona_leds(int estado, int estados_dos_leds[]);
  // Muda o estado de LED(s) para ligado (se {estado} = 1)
  // ou desligado (se {estado} = 0.
  // O byte seguinte ao codigo do comando deve ser uma letra maiuscula identificando
  // o numero do LED ('A' = 0, 'B' = 1, etc.); ou '@' para
  // sgnificar "todos os LEDs".

// DEBUGAGEM

void mostra_byte(char *mensagem, int byte);
  // Excreve na porta serial uma linha "# {mensagem} = '{c}'"
  // onde {c} eh o caracter com codigo ASCII {byte}.

void mostra_comando(int comando);
  // Excreve na porta serial uma linha "# Comando recebido = '{c}'"
  // onde {c} eh o caracter com codigo ASCII {comando}.

#endif
