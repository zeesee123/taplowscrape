from tqdm import tqdm
import time

for i in tqdm(range(10), desc="Testing tqdm", ncols=70):
    time.sleep(0.2)