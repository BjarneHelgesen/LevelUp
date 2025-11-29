  python -m cProfile -o profile.prof smoketest.py
  snakeviz profile.prof
@ rem # python -m pstats profile.prof 
@ rem sort cumtime
@ rem stats 100 