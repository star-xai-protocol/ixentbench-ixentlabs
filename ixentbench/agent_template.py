# -*- coding: utf-8 -*-
"""
iXentBench — Agent Template (Option C)
This is a minimalist agent example. 
It receives the game state via STDIN (JSON) and returns a move via STDOUT (JSON).
"""
import sys
import json

def main():
    # 1. Read the game state sent by the SDK
    try:
        input_data = sys.stdin.read()
        if not input_data:
            return
        state = json.loads(input_data)
    except Exception as e:
        # In case of an error, we cannot write anything to STDOUT other than the final JSON
        return

    # 2. Decision logic (This is where your strategy goes)
    # Example: Always try to move mouse 1 to tile P21
    # state['data']['inventory'] contains your available gears, etc.
    
    move = {
        "command": "G1@P21(b=0)+90", # Example command
        "reasoning": "Basic agent attempting initial positioning at P21."
    }

    # 3. Return the move to the SDK
    print(json.dumps(move))

if __name__ == "__main__":
    main()