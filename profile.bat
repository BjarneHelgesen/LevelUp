  python -m cProfile -o smoketest.prof smoketest.py
  snakeviz smoketest.prof
# python -m pstats smoketest.prof 
# sort cumtime
# stats 100 