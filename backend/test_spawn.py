import multiprocessing
import os
import sys

if __name__ == "__main__":
    multiprocessing.set_start_method('spawn')
    print("Spawning child...")
    def target():
        print("Child started, importing fastapi...")
        from fastapi.cli import main
        print("Child imported fastapi.")
    
    p = multiprocessing.Process(target=target)
    p.start()
    p.join()
