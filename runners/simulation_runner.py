import os

import numpy as np
from sklearn.decomposition import FastICA

from data.imca import generate_synthetic_data
from metrics.mcc import mean_corr_coef
from models.icebeem_wrapper import ICEBEEM_wrapper
from models.ivae.ivae_wrapper import IVAE_wrapper
# from models.tcl.tcl_wrapper_gpu import TCL_wrapper
import wandb


def run_ivae_exp(args, config):
    """run iVAE simulations"""
    data_dim = config.data_dim
    n_segments = config.n_segments
    n_layers = config.n_layers
    n_obs_per_seg = config.n_obs_per_seg
    data_seed = config.data_seed

    max_iter = config.ivae.max_iter
    iter_dict = {2: 70000, 4: 70000}  # 100000
    lr = config.ivae.lr
    cuda = config.ivae.cuda

    results = {l: {n: [] for n in n_obs_per_seg} for l in n_layers}

    nSims = args.nSims
    dataset = args.dataset
    test = args.test
    for l in n_layers:
        for n in n_obs_per_seg:
            x, y, s = generate_synthetic_data(data_dim, n_segments, n, l, seed=data_seed,
                                              simulationMethod=dataset, one_hot_labels=True, varyMean=False)
            for seed in range(nSims):
                print('Running exp with L={} and n={}; seed={}'.format(l, n, seed))
                # run iVAE
                ckpt_file = os.path.join(args.checkpoints, 'ivae_{}_l{}_n{}_s{}.pt'.format(dataset, l, n, seed))
                res_iVAE = IVAE_wrapper(X=x, U=y, n_layers=3, hidden_dim=data_dim * 2,
                                        cuda=cuda, max_iter=iter_dict[l], lr=lr,
                                        ckpt_file=ckpt_file, seed=seed, test=test)

                # store results
                results[l][n].append(max(mean_corr_coef(res_iVAE[0].detach().numpy(), s),
                                         mean_corr_coef(res_iVAE[2]['encoder'][0].detach().numpy(), s),
                                         mean_corr_coef(
                                             FastICA().fit_transform(res_iVAE[2]['encoder'][0].detach().numpy()), s)))
                print(results[l][n])
    # prepare output
    Results = {
        'data_dim': data_dim,
        'data_segments': n_segments,
        'CorrelationCoef': results
    }

    return Results


def run_icebeem_exp(args, config):
    """run ICE-BeeM simulations"""
    data_dim = config.data_dim
    n_segments = config.n_segments
    n_layers = config.n_layers
    n_obs_per_seg = config.n_obs_per_seg
    data_seed = config.data_seed
    use_sem = config.use_sem
    chain=config.chain

    try:
        lr_flow = config.icebeem.lr_flow
        lr_ebm = config.icebeem.lr_ebm
        n_layers_flow = config.icebeem.n_layers_flow
        ebm_hidden_size = config.icebeem.ebm_hidden_size
        use_strnn = config.icebeem.use_strnn
    except:
        lr_flow = config.lr_flow
        lr_ebm = config.lr_ebm
        n_layers_flow = config.n_layers_flow
        ebm_hidden_size = config.ebm_hidden_size
        use_strnn = config.use_strnn

    if not isinstance(n_layers, list):
        n_layers = [n_layers]
    if not isinstance(n_obs_per_seg, list):
        n_obs_per_seg = [n_obs_per_seg]

    results = {l: {n: [] for n in n_obs_per_seg} for l in n_layers}

    nSims = args.nSims
    dataset = args.dataset
    test = args.test

    for l in n_layers:
        for n in n_obs_per_seg:
            x, y, s = generate_synthetic_data(data_dim, n_segments, n, l, seed=data_seed,
                                              simulationMethod=dataset, one_hot_labels=True, use_sem=use_sem, chain=chain)
            for seed in range(nSims):
                if nSims ==1:
                    try:
                        seed = wandb.config.seed
                    except:
                        seed = config.data_seed
                print('Running exp with L={} and n={}; seed={}'.format(l, n, seed))
                # generate data

                n_layers_ebm = l + 1
                ckpt_file = os.path.join(args.checkpoints, 'icebeem_{}_l{}_n{}_s{}.pt'.format(dataset, l, n, seed))
                recov_sources = ICEBEEM_wrapper(X=x, Y=y, S=s, ebm_hidden_size=ebm_hidden_size,
                                                n_layers_ebm=n_layers_ebm, n_layers_flow=n_layers_flow,
                                                lr_flow=lr_flow, lr_ebm=lr_ebm, seed=seed, ckpt_file=ckpt_file,
                                                test=test,use_strnn=use_strnn,use_chain=chain)

                # store results
                results[l][n].append(np.max([mean_corr_coef(z, s) for z in recov_sources]))
                print(f"MCC={(mcc:=np.max([mean_corr_coef(z, s) for z in recov_sources]))}")


    # prepare output
    Results = {
        'data_dim': data_dim,
        'data_segments': n_segments,
        'CorrelationCoef': results
    }

    return Results


# def run_tcl_exp(args, config):
#     """run TCL simulations"""
#     stepDict = {1: [int(5e3), int(5e3)], 2: [int(1e4), int(1e4)], 3: [int(1e4), int(1e4)], 4: [int(1e4), int(1e4)],
#                 5: [int(1e4), int(1e4)]}
#
#     data_dim = config.data_dim
#     n_segments = config.n_segments
#     n_layers = config.n_layers
#     n_obs_per_seg = config.n_obs_per_seg
#     data_seed = config.data_seed
#
#     results = {l: {n: [] for n in n_obs_per_seg} for l in n_layers}
#     results_no_ica = {l: {n: [] for n in n_obs_per_seg} for l in n_layers}
#
#     num_comp = data_dim
#
#     nSims = args.nSims
#     dataset = args.dataset
#     test = args.test
#
#     for l in n_layers:
#         for n in n_obs_per_seg:
#             # generate data
#             x, y, s = generate_synthetic_data(data_dim, n_segments, n, l, seed=data_seed,
#                                               simulationMethod=dataset, one_hot_labels=False)
#             for seed in range(nSims):
#                 print('Running exp with L={} and n={}; seed={}'.format(l, n, seed))
#                 # checkpointing done in TF is more complicated than pytorch, create a separate folder per arg tuple
#                 ckpt_folder = os.path.join(args.checkpoints, args.dataset, str(l), str(n), str(seed))
#                 # run TCL
#                 res_TCL = TCL_wrapper(sensor=x.T, label=y, random_seed=seed,
#                                       list_hidden_nodes=[num_comp * 2] * (l - 1) + [num_comp],
#                                       max_steps=stepDict[l][0] * 2, max_steps_init=stepDict[l][1],
#                                       ckpt_dir=ckpt_folder, test=test)
#                 # store results
#                 mcc_no_ica = mean_corr_coef(res_TCL[0].T, s ** 2)
#                 mcc_ica = mean_corr_coef(res_TCL[1].T, s ** 2)
#                 print('TCL mcc (no ICA): {}\t mcc: {}'.format(mcc_no_ica, mcc_ica))
#                 results[l][n].append(mcc_ica)
#                 results_no_ica[l][n].append(mcc_no_ica)
#
#     # prepare output
#     Results = {
#         'data_dim': data_dim,
#         'data_segments': n_segments,
#         'CorrelationCoef': results,
#         'CorrelationCoef_no_ica': results_no_ica,
#     }
#
#     return Results
