# Semantic-Forward Relaying: A Novel Framework Towards 6G Cooperative Communications
Example codes for the paper “Semantic-Forward Relaying: A Novel Framework Towards 6G Cooperative Communications”, which has been accepted for publication in IEEE Communications Letters with DOI: 10.1109/LCOMM.2024.3352916.

arXiv: https://arxiv.org/abs/2310.07987
IEEE Xplore: https://ieeexplore.ieee.org/document/10388241

## Instruction

Tested with
- python 3.7.16
- pytorch 1.13.0

### Steps
Run with the pre-trained semantic neural network:
- Directly run “Semantic_Forward.py” with the pre-trained semantic neural network “semantic_coder.pkl” to test the semantic forward systems.

Or training from the beginning:
- Run “googlenet_train.py” to obtain neural network for classifier.
- Run “ENC_DEC_train.py” to obtain neural network for semantic encoder and decoder.
- Run “Semantic_Forward.py” to test the semantic forward systems.

## Notes
The source codes of LDPC are revised from the codes in: https://github.com/hichamjanati/pyldpc

The source codes of example semantic neural network, “googlenet_train.py” and “ENC_DEC_train.py”, are revised from the codes in: https://github.com/SJTU-mxtao/Semantic-Communication-Systems

This framework can be adaptive to other semantic neural network by revising the class “SemanticNN” in “Semantic_Forward.py”.

## Citation
BibTeX infomation:
```
@Article{lin2023SF,
  author  = {Wensheng Lin and Yuna Yan and Lixin Li and Zhu Han and Tad Matsumoto},
  journal = {IEEE Communications Letters},
  title   = {Semantic-Forward Relaying: {A} Novel Framework Towards 6{G} Cooperative Communications},
  year    = {2024},
  doi     = {10.1109/LCOMM.2024.3352916},
}
```

