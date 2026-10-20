import argparse
from pathlib import Path
from .benchmark import run

parser = argparse.ArgumentParser(description='Run the retrospective GFP active-learning benchmark.')
parser.add_argument('--data-dir',type=Path,default=Path('data'))
parser.add_argument('--output-dir',type=Path,default=Path('results'))
args=parser.parse_args()
result=run(args.data_dir,args.output_dir)
print(f"Completed {len(result['seeds'])} seeds, {len(result['strategies'])} policies; outputs in {args.output_dir}")
