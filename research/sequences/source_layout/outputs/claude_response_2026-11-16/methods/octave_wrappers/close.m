function close(varargin)
% Local headless UI shim: upstream only closes the waitbar handle zero.
  if nargin == 1 && isnumeric(varargin{1}) && isequal(varargin{1},0)
    return;
  end
  error('Unexpected non-waitbar call to the narrowly scoped headless close shim');
end
