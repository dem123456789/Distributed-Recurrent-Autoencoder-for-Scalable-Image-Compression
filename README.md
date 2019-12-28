# Distributed Recurrent Autoencoder for Scalable Image Compression
This is an implementation of [DRASIC: Distributed Recurrent Autoencoder for Scalable Image Compression](https://arxiv.org/abs/1903.09887)
![slepianwolf](/img/slepianwolf.png)
![deepdsc](/img/deepdsc.png)
![deepencoderdecoder](/img/deepencoderdecoder.png)

## Requirements
 - Python 3
 - PyTorch 1.0

## Results
- Rate-distortion curves for data sources distributed by random subsets with T = 16 for all sources.

![full_subset_band](/img/full_subset_band.png)

- Rate-distortion curves for data sources distributed by class labels with T = 16 for all sources.

![half_class_band](/img/full_class_band.png)

- Rate-distortion curves for data sources distributed by random subsets with T=16 for the first half of sources and $T=8$ for the second half of sources.

![half_class_band](/img/half_subset_band.png)

- Rate-distortion curves for data sources distributed by class labels with T=16 for the first half of sources and $T=8$ for the second half of sources.

![half_class_band](/img/half_class_band.png)

## Acknowledgement
*Enmao Diao  
Jie Ding  
Vahid Tarokh*
