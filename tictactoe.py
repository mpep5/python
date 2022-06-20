#!/usr/local/bin/python3

## TIC TAC TOE ##
# Mike Pepe
# Completed 40 years ago, reproduced here from scratch June 19, 2022
#

## pseudo-code
# 1. welcome, choose PvP, PvC, CvC (Player, Computer, Teaching mode)
# 2. clear board
# 3. draw board
# 4. player 1 moves, record move and board to list
#   a. person, ask for move, validate entry
#   b. computer, match board to history, choose most winning next move
#   c. computer, pick move at random for teaching mode
# 5. is it a win?  no, continue.  yes, record and start over.
# 6. next player moves
# 7. repeat with draw board
# 8. game over, write win/loss to list, then append to file
# left-to-right, beginning in top-left corner

#
# Import Modules
#
import time
import random

#
# Global variables
#
xwins = 0
owins = 0
nowins = 0

#
# Functions
#
def clear_board():
  board=[0,0,0,0,0,0,0,0,0]
  return(board)

def draw_board(board,mode):
  if (mode == "D"):
    for square in range(len(board)):
      if (board[square] == 0):
        print("-",end = "")
      if (board[square] == 1):
        print("X",end = "")
      if (board[square] == 2):
        print("O",end = "")
      if (((square+1) % 3) == 0):
        print()
      else:
        print("|",end = "")
    print()
    time.sleep(1)

def choose_random_square(board):
  while(True):
    choice = random.randint(0,8)
    if (board[choice] == 0):
      return(choice)

def update_board(board,choice,player):
  board[choice]=player
  return(board)

def change_player(player):
  if (player == 1):
    player = 2
  else:
    player = 1
  return(player)
 
def check_for_win(board):
  horizontal = [0,3,6]
  vertical = [0,1,2]
  for x in horizontal:
    if (board[0+x] == board[1+x] == board[2+x] != 0):
      return(True)
  for x in vertical:
    if (board[0+x] == board[3+x] == board[6+x] != 0):
      return(True)
  if (board[0] == board[4] == board[8] != 0):
    return(True)
  if (board[2] == board[4] == board[6] != 0):
    return(True)
  return(False)

def check_for_end(move):
  if (move == 9):
    return(True)
  else:
    return(False)

def declare_winner(player,mode):
  global xwins
  global owins
  if (player == 1):
    winner = "X"
    xwins = xwins + 1
  elif (player == 2):
    winner = "O"
    owins = owins + 1
  if (mode == "D"):
    print()
    print("And the winner is... ",winner,"!!!")
    print()
    time.sleep(3)

def declare_tie(mode):
  global nowins
  nowins = nowins + 1
  if (mode == "D"):
    winner = "the Cat"
    print()
    print("And the winner is... ",winner,"!!!")
    print()
    time.sleep(3)

#
# Play a game
#
def play_a_game(mode):
  board = clear_board()
  draw_board(board,mode)
  win = False
  cat = False
  player = 1
  move = 0
  while(not win):
    move = move + 1
    choice = choose_random_square(board)
    board = update_board(board,choice,player)
    draw_board(board,mode)
    win = check_for_win(board)
    if win:
      declare_winner(player,mode)
      break
    end = check_for_end(move)
    if end:
      declare_tie(mode)
      break
    player = change_player(player)

#
# Main Code Section
#
def main():
  mode = ""
  games = 0
  while (mode != "D" and mode != "L"):
    mode = input("Would you like to use Display mode or Computer Learn mode [D/L]? ")
  while (games < 1):
    games = input("How many consecutive games would you like to play? ")
    games = int(games)
  print("...playing...")
  start_time = time.time()
  start_process = time.process_time()
  for game_number in range(games):
    play_a_game(mode)
  end_process = time.process_time()
  end_time = time.time()
  elapsed_time = round(end_time - start_time,2)
  process_time = round(end_process - start_process,4)
  print(games,"games were played in",elapsed_time,"seconds.")
  print("Processor time utilized:",process_time,"seconds.")
  xwin_rate = round((xwins / games * 100),2)
  owin_rate = round((owins / games * 100),2)
  nowin_rate = round((nowins / games * 100),2)
  print("X won",xwins,"times.  Win rate",xwin_rate,"%.")
  print("O won",owins,"times.  Win rate",owin_rate,"%.")
  print("The cat won",nowins,"times.  Win rate",nowin_rate,"%.")


#
# Go time...
#
main()
exit(0)

