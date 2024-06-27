# OCP Compliance Tool
The goal of the OCP compliance tool is to provide a set of acceptance tests for GPU baseboards in hyperscale environment. 

[**ocp-diag-ctam**](https://github.com/opencomputeproject/ocp-diag-ctam) is a collaboration between datacenter hyperscalers and Nvidia is contributing to this open source project.

The *ocp-diag-ctam* directory under *sps-tool* is a [git subtree](https://www.atlassian.com/git/tutorials/git-subtree)(a nested repo) where the upstream repo is [**ocp-diag-ctam**](https://github.com/opencomputeproject/ocp-diag-ctam).

The sub-project ocp-diag-ctam does not auto-sync to its upstream. The command to update the sub-project at a later date is following:
```bash
git fetch https://github.com/opencomputeproject/ocp-diag-ctam.git <branch-name>

git subtree pull --prefix ocp-diag-ctam https://github.com/opencomputeproject/ocp-diag-ctam.git <branch-name>
```
*Note: Ideally, we should be synced with upstream **main** branch.*
**WARNING**: ocp-diag-ctam is currently synced with upstream *developer* branch as changes have not been merged into *main* yet.

## Getting onboard
Please refer to [**OCP Tool Confluence Page**](https://confluence.nvidia.com/display/SPS/OCP+Compliance+Tool+-+CTAM#OCPComplianceToolCTAM-Howtoonboard?).

## Usage
Please refer to README in ocp-diag-ctam directory for usage.
