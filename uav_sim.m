tic

% MATLAB's python instance might need to be told where to find the usr
% python modules.
needed_python_path = '/usr/local/lib/python2.7/site-packages';
python_path = py.sys.path;
if count(python_path,p) == 0
insert(python_path,int32(0),needed_python_path);
end

runs_per_batch = int8(100);
run_batch = @(in) py.sim.batch_run(runs_per_batch,...
    in(1),int8(in(2)),int8(in(3)));

% For each parameter, we define a min and max value so that we can limit
% the scope of our inveistigation and so that it is compatible with
% sampling from a latin hypercube design.
dist_range = [5e3,5e4];
uav_range = [1,20];
cwis_range = [0,5];

num_params = 3;
num_batches = 100;

data = lhsdesign(num_batches, num_params);
data(:,1) = data(:,1)*diff(dist_range) + dist_range(1);
data(:,2) = round(data(:,2)*diff(uav_range) + uav_range(1));
data(:,3) = round(data(:,3)*diff(cwis_range) + cwis_range(1));

result = nan(num_batches,1);

for ii = 1:num_batches
    result(ii) = run_batch(data(ii,:));
end


toc