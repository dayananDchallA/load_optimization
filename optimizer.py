import pandas as pd

from ortools.linear_solver import pywraplp
import warnings
warnings.filterwarnings('ignore')

data_url = "data/examples.csv"
dataset = pd.read_csv(data_url)

# Get the volume of items
dataset['Volume'] = dataset['Actual Weight'] * dataset['Actual Height'] * dataset['Actual Length']

# Calculate the total weight and total volume of all items

total_volume = dataset['Volume'].sum()
total_weight = dataset['Actual Weight'].sum()

print('Total Volume: ', total_volume, 'cm3')
print('Total Weight: ', total_weight, ' kg')

FEET_TO_CM = 30.48
lorries = [
    {
        "code": "4x4",
        "description": "4x4 Pickup",
        "length": 4,
        "height": 3,
        "width": 3.5,
        "max_weight": 500
    },
    {
        "code": "VAN",
        "description": "Van",
        "length": 8,
        "height": 3,
        "width": 3.5,
        "max_weight": 500
    }, 
    {
        "code": "LORRY-S",
        "description": "1-tonne lorry",
        "length": 10,
        "height": 5,
        "width": 5,
        "max_weight": 1000
    },
    {
        "code": "LORRY-M",
        "description": "3-tonne lorry",
        "length": 14,
        "height": 7.2,
        "width": 7,
        "max_weight": 3000
    },
    {
        "code": "LORRY-L",
        "description": "5-tonne lorry",
        "length": 17,
        "height": 7.2,
        "width": 7,
        "max_weight": 5000
    }    
]
for lorry in lorries:
    volume = round((lorry['length'] * FEET_TO_CM) * (lorry['height'] * FEET_TO_CM) * (lorry['width'] * FEET_TO_CM), 2)
    lorry['max_volume'] = volume

print(lorries)

# create data model for knapsack problem 
# paramter optimize are data to be packing into the available vehicle in totalLorry
def create_data_model(optimize, totalLorry):
    """Create the data for the example."""
    data = {}
    weights = optimize['Actual Weight'].to_list()
    volumes = optimize['Volume'].to_list()
    
    data['weights'] = weights
    data['volumes'] = volumes
    
    data['items'] = list(range(len(weights)))
    data['num_items'] = len(weights)
    
    max_volumes = []
    max_weights = []
    truck_types = []
    
    # reserve totalLorry data to be starting from small vehicle first
    totalLorry.reverse()

    # resgister max_weight and max_volume for each available vehicle
    for tL in totalLorry:
        for i in range(tL['number']):
            max_volumes.append(tL['max_volume'])
            max_weights.append(tL['max_weight'])
            truck_types.append(tL['code'])
    
    data['max_volume'] = max_volumes 
    data['max_weight'] = max_weights 
    data['truck_types'] = truck_types
    
    data['trucks'] = list(range(len(data['max_volume'])))
    
    return data

# ===============================
# ==== Get Load Optimization ====
# ===============================

totalLorry = [{'code': 'LORRY-L',
  'number': 1,
  'max_weight': 5000,
  'max_volume': 24261874.16},
 {'code': 'LORRY-M',
  'number': 2,
  'max_weight': 3000,
  'max_volume': 19980366.96},
 {'code': 'LORRY-S',
  'number': 3,
  'max_weight': 1000,
  'max_volume': 7079211.65},
 {'code': 'VAN', 'number': 3, 'max_weight': 500, 'max_volume': 2378615.11},
 {'code': '4x4', 'number': 6, 'max_weight': 500, 'max_volume': 1189307.56}]

data = create_data_model(dataset, totalLorry)

# Create the mip solver with the SCIP backend.
solver = pywraplp.Solver.CreateSolver('SCIP')

# Variables
# x[i, j] = 1 if item i is packed in bin j.
x = {}
for i in data['items']:
    for j in data['trucks']:
        x[(i, j)] = solver.IntVar(0, 1, 'x_%i_%i' % (i, j))

# Constraints
# Each item can be in at most one bin.
for i in data['items']:
    solver.Add(sum(x[i, j] for j in data['trucks']) <= 1)

# The amount packed in each bin cannot exceed its max weight.
for j in data['trucks']:
    solver.Add(
        sum(x[(i, j)] * data['weights'][i]
            for i in data['items']) <= data['max_weight'][j])

# The amount packed in each bin cannot exceed its max volume.
for j in data['trucks']:
    solver.Add(
        sum(x[(i, j)] * data['volumes'][i]
            for i in data['items']) <= data['max_volume'][j])


# Add objectives
objective = solver.Objective()

for i in data['items']:
    for j in data['trucks']:
        objective.SetCoefficient(x[(i, j)], data['volumes'][i])
objective.SetMaximization()


status = solver.Solve()

_totalLeftVolume = 0
_totalLeftWeight = 0
if status == pywraplp.Solver.OPTIMAL:
    assign = []
    total_weight = 0
    total_items = 0
    print('Total Lorry: ')
    print(totalLorry)
    print()
    print('Total Items:', len(dataset))
    print()
    for j in data['trucks']:
        bin_weight = 0
        bin_volume = 0
        print('Truck ', j, '[', data['truck_types'][j] ,'] - max_weight:[', "{:,.2f}".format(data['max_weight'][j]), '] - max volume:[', "{:,.2f}".format(data['max_volume'][j]), ']' )
        for i in data['items']:
            if x[i, j].solution_value() > 0:
                assign.append(i)
                total_items += 1
                print('Item', i, '- weight:', data['weights'][i],
                      ' volumes:', data['volumes'][i])
                bin_weight += data['weights'][i]
                bin_volume += data['volumes'][i]

        print('Packed truck volume:', "{:,.2f}".format(bin_volume))
        print('Packed truck weight:', "{:,.2f}".format(bin_weight))
        print()

        if (bin_volume > 0) & (bin_weight > 0):
            leftVolume = data['max_volume'][j] - bin_volume
            leftWeight = data['max_weight'][j] - bin_weight
        else:
            leftVolume = 0
            leftWeight = 0

        print('Left Volume', "{:,.2f}".format(leftVolume))
        print('Left Weight', "{:,.2f}".format(leftWeight))
        print()
        print()

        total_weight += bin_weight
        _totalLeftVolume += leftVolume
        _totalLeftWeight += leftWeight

    print('Total packed weight:', "{:,.2f}".format(total_weight))
    print('Total packed volume:', "{:,.2f}".format(objective.Value()))
    print('Total item assigned:', "{:,.0f}".format(total_items))
    print()
    print("#" * 100)
    print('Total Left Volume', "{:,.2f}".format(_totalLeftVolume))
    print('Total Left Weight', "{:,.2f}".format(_totalLeftWeight))
    print("#" * 100)

else:
    print('The problem does not have an optimal solution.')

print()