##----------------------------------------------------------------------
## run.slurm
## Owen Travis
## For launching a Slurm job on the Della cluster at Princeton Research
## Computing. This file is heavily based on materials published by
## Princeton Research Computing:
## https://researchcomputing.princeton.edu/support/knowledge-base/slurm
##----------------------------------------------------------------------

#!/bin/bash
#SBATCH --job-name=Tra-Feb24     # create a short name for your job
#SBATCH --output=slurm-%A.%a.out # stdout file
#SBATCH --error=slurm-%A.%a.err  # stderr file
#SBATCH --nodes=1                # node count
#SBATCH --ntasks=1               # total number of tasks across all nodes
#SBATCH --cpus-per-task=1        # cpu-cores per task (>1 if multi-threaded tasks)
#SBATCH --mem=4G                 # memory (4G per core)
#SBATCH --gres=gpu:1             # number of gpus per node
#SBATCH --time=023:00:00         # total run time limit (HH:MM:SS)
#SBATCH --array=1-300            # job array with index values 0, 1, 2, 3, 4
#SBATCH --mail-type=all          # send email on job start, end and fault
#SBATCH --mail-user=redacted@domain.com

echo "My SLURM_ARRAY_JOB_ID is $SLURM_ARRAY_JOB_ID."
echo "My SLURM_ARRAY_TASK_ID is $SLURM_ARRAY_TASK_ID"
echo "Executing on the machine:" $(hostname)

module purge
module load anaconda3/2021.11
conda activate kata-env

python -u accuracy.py
