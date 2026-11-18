% Wrapper around the published, unmodified numerical MATLAB files. GNU Octave
% execution is recorded as GNU Octave, never as MATLAB execution. Numeric CSV:
% time in years (UTC seconds / 31557600), latitude, longitude, reported M.
% args: input_csv output_mat b df [frozen_cut_log10]
args = argv();
here = fileparts(mfilename('fullpath'));
source = fullfile(here,'..','authors_2013_exact','eq_cluster');
addpath(source);
addpath(here,'-begin');
input = dlmread(args{1},',');
time = input(:,1);
Lat = input(:,2); Lon = input(:,3); mag = input(:,4);
b = str2double(args{3}); df = str2double(args{4}); p=.5;
[P,n,D,T,M] = bp(time,mag,Lon,Lat,[],b,df,Inf,0);
TN = T .* 10.^(-p*b*M);
RN = D.^df .* 10.^(-(1-p)*b*M);
eta_log10 = log10(TN .* RN); % author's fitting/plot expression
cut_eta_log10 = log10(TN) + log10(RN); % author's edge-cut expression
finite_eta_mask = isfinite(real(eta_log10)) & imag(eta_log10)==0;
if length(args) < 5
  % This invokes the complete published cluster_analysis script, including its
  % normalmix_1D, descend_all, family assignment, and operational main/fore/aft.
  % Only the three GUI functions are shadowed by narrowly scoped local shims.
  cluster_analysis;
  cut_source = 'unmodified authors normalmix_1D and cluster_analysis';
else
  % A frozen development cut is intentionally an adapter for held-out analysis,
  % not a claim that the original script exposes a frozen-threshold option.
  c = str2double(args{5});
  P1=P'; P1(find(cut_eta_log10 > c))=0;
  roots=find(P1==0);
  Pfin=zeros(size(P)); Imain=[]; Ifor=[]; Iaft=[];
  for i=1:length(roots)
    [I,delta] = descend_all(P1,roots(i));
    [mmax,imax] = max(mag(I)); IM=I(imax);
    Pfin(I)=IM;
    Imain(end+1)=IM;
    Ifor=[Ifor I(find(time(I)<time(IM)))];
    Iaft=[Iaft I(find(time(I)>time(IM)))];
  end
  mu1=NaN;mu2=NaN;sigma1=NaN;sigma2=NaN;A=NaN;A2=NaN;
  cut_source='adapter: held-out cut, authors bp and descend_all unmodified';
end
% Preserve upstream first-main indexing; map to the paper's three roles without
% calling a singleton physically independent or a statistical family causal.
role=zeros(size(P)); role(:)=2;
for i=1:length(Imain)
  root=Imain(i); count=sum(Pfin==root);
  if count==1, role(root)=0; else role(root)=1; end
end
source_commit='636d07beb89bde7d7deb502db78beebb45528cca';
octave_version=version();
save('-mat7-binary',args{2},'P','n','D','T','M','TN','RN','eta_log10','cut_eta_log10',
     'Pfin','Imain','Ifor','Iaft','role','c','mu1','mu2','sigma1','sigma2','A','A2',
     'b','df','source_commit','octave_version','cut_source','finite_eta_mask');
fprintf('AUTHOR_2013_COMPLETED n=%d b=%.17g df=%.17g cut=%.17g version=%s\n',length(time),b,df,c,octave_version);
