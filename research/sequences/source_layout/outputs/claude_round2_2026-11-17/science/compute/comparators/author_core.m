% Private timing wrapper; numerical bp and latlonkm are the pinned original.
args=argv(); here=fileparts(mfilename('fullpath'));
% Resolve repository path from the explicit argument instead of cwd or HOME.
source=args{3}; shims=args{4}; addpath(source); addpath(shims,'-begin');
data=dlmread(args{1},','); time=data(:,1); Lat=data(:,2);Lon=data(:,3);mag=data(:,4);
warm_clock=tic();[Pw,nw,Dw,Tw,Mw]=bp(time(1:64),mag(1:64),Lon(1:64),Lat(1:64),[],1,1.6,Inf,0);warmup_seconds=toc(warm_clock);
clock=tic();[P,n,D,T,M]=bp(time,mag,Lon,Lat,[],1,1.6,Inf,0);kernel_seconds=toc(clock);
octave_version=version();source_commit='636d07beb89bde7d7deb502db78beebb45528cca';
save('-mat7-binary',args{2},'P','n','D','T','M','kernel_seconds','warmup_seconds','octave_version','source_commit');
fprintf('AUTHOR_CORE n=%d seconds=%.17g version=%s\n',length(time),kernel_seconds,octave_version);

