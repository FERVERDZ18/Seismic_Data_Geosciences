function varargout = set(varargin)
% Local headless UI shim only for set(waitbar_handle,'Name',...);
  if nargin >= 2 && isnumeric(varargin{1}) && isequal(varargin{1},0) && strcmp(varargin{2},'Name')
    varargout = {};
    return;
  end
  [varargout{1:nargout}] = builtin('set',varargin{:});
end
