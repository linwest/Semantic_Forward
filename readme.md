# Semantic-Forward Relaying: A Novel Framework Towards 6G Cooperative Communications
Example codes for the paper “Semantic-Forward Relaying: A Novel Framework Towards 6G Cooperative Communications”.

arXiv: https://arxiv.org/abs/2310.07987


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
@article{lin2023SF,
  title={Semantic-Forward Relaying: {A} Novel Framework Towards 6G Cooperative Communications},
  author={Wensheng Lin and Yuna Yan and Lixin Li and Zhu Han and Tad Matsumoto},
  journal={arXiv preprint arXiv:2310.07987},
  year={2023}
}
```

