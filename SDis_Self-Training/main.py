from process import process_data
from mainFunctions.basic import createFolder
from config import ROOT_DIR
import argparse
import json

def main():
    parser = argparse.ArgumentParser(description='Parameters for multi-output disaggregation with RF and GB')
    parser.add_argument('--attr_value', nargs='+', required=True, help='Input population groups')
    parser.add_argument('--city', type=str,  help='City, case study area')
    parser.add_argument('--group_split', nargs='+', type=int, required=True, help='Points to split the demographic groups')
    parser.add_argument('--nmodelpred', type=int, help='Average with flipped images')
    parser.add_argument('--popraster', type=str, default='GHS_POP_100_near_cubicspline.tif', help='GHS input layer')
    parser.add_argument('--key', type=str, help='Common key between shp and csv')
    parser.add_argument('--run_Pycno', type=str, default='no', help='Run pycnophylactic interpolation')
    parser.add_argument('--run_Dasy', type=str, default='no', help='Run dasymetric mapping')
    parser.add_argument('--run_Disaggregation', type=str, default='no', help='Run disaggregation')
    parser.add_argument('--maxIters',default=10, type=int,  choices=range(2, 101), help='Max Iterations')
    parser.add_argument('--methodopts', nargs='+', help='Select method of disaggregation (aplm (linear model), aprf (random forest), apcatbr (Catboost Regressor))')
    #choices = ['aplm', 'aprf', 'apcatbr']
    parser.add_argument('--ymethodopts',  nargs='+', help='Input layers')
    parser.add_argument('--inputDataset', nargs='+', help='Training dataset')
    parser.add_argument('--verMassPreserv', type=str, default='no', help='Verify mass preservation')
    parser.add_argument('--run_Evaluation', type=str, default='no', help='Evaluation of results')

    args, unknown = parser.parse_known_args()
    #args = parser.parse_args()
    
    print('----- Arguments successfully passed -----')
    createFolder(ROOT_DIR + '/logs')
    with open(ROOT_DIR + '/logs/commandline_args.txt', 'w') as f:
        json.dump(args.__dict__, f, indent=2)

    with open(ROOT_DIR + '/logs/commandline_args.txt', 'r') as f:
        args.__dict__ = json.load(f)

    process_data(attr_value=args.attr_value, city=args.city, group_split=args.group_split, nmodelpred=args.nmodelpred, popraster = args.popraster, key=args.key, 
            run_Pycno=args.run_Pycno, run_Dasy=args.run_Dasy, run_Disaggregation = args.run_Disaggregation, maxIters = args.maxIters, methodopts=args.methodopts, ymethodopts=args.ymethodopts, 
            inputDataset=args.inputDataset, verMassPreserv=args.verMassPreserv, run_Evaluation=args.run_Evaluation)

if __name__ == '__main__':
    main()
    