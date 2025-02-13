# Change env, and show it
source ~/anaconda3/etc/profile.d/conda.sh
conda init bash
conda activate pytorch_p38
conda env list 

# Install dgl-cuda, this can't use pip, so can't use requirements
conda install -c dglteam dgl-cuda11.1
conda install -c conda-forge rdkit=2019.09.2
# this step already updated in the requirements file
# pip install dgl-cu111==0.6.1