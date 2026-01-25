FILE STRUCTURE

Version 1

# HEADS UP!
This is all brainstorm, this might be changed when intigration begins.

## Structure

Every step is structured in a JSON, where each step is a designated number. The steps go from lowest (first) to highest (last)

The steps itself can have 3 types:
- keyboard
- mouse
- application

these are what the step of the macro will be controlled.

### Type: KEYBOARD

Keyboard takes these values:

- actiontype
    > this can be "singlekey", which signals the macro that it will be only one key. this should also support combo keys like ^C etc, because shell accepts those as one key.
    > it can also be "multikey", signaling what the macro should press at once.
- actiondata
    > this is a list of the keys that should be pressed. for single, itll only contain one, for mult, itll contain a list of all keys. they will be pressed at the same time.
- sleep
    > this is a int in MS that makes the macro wait that long untill it starts the action
- presssleep
    > Press sleep is how long the key will be held down.

### Type: MOUSE

Mouse takes these values:
- actiontype
    > Can either be move or click. Self explanitory. Move tells the macro to move the mouse, click tell it to click.
- actiondata
    > IF MOVE: Takes two floats. Absolute coordinates of the screen. 0,0 is top left, 1,1 is bottom right.
    > IF CLICK: Takes one int. 0 is left click, 1 is rightclick.
- sleep
    > this is a int in MS that makes the macro wait that long untill it starts the action
- presssleep (IF CLICK)
    > Press sleep is how long the key will be held down.
- transition (IF MOVE)
    > The type of movement for the mouse. quadratic is smooth, linear is... linear!
    > Function for linear = M(t)=t
    > Function for quadratic = M(t)=2t^2 - t^4 D=[0|1]
- transitiontime (IF MOVE)
    > How long the mouse should be moved to the final desination in MS

### Type: APPLICATION
- actiontype
    > can either be open or close. open tells the script to open an application, close tells it to close.
- actiondata
    IF OPEN
    > You can open an application using a shell command or a absolute path. Examples for shell is taskmgr or notepad.
    IF CLOSE
    > You can close applications that were opened within the same macro with its step id. Or you can use the task name to kill it. Be careful though.
- sleep
    > this is a int in MS that makes the macro wait that long untill it starts the action

# 