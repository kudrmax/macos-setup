# ~/.zshenv — загружается для ВСЕХ типов шеллов (interactive, non-interactive, scripts)
# Только лёгкие операции: переменные и PATH

export NVM_DIR="$HOME/.nvm"

# Default node в PATH без загрузки nvm.sh
# Резолвит partial alias (напр. "22" → v22.22.0)
if [[ -r "$NVM_DIR/alias/default" ]]; then
  _nvm_default=$(<"$NVM_DIR/alias/default")
  _nvm_default="${_nvm_default#v}"
  _nvm_node_dirs=("$NVM_DIR/versions/node"/v${_nvm_default}*(Nn))
  if (( ${#_nvm_node_dirs} )); then
    path=("${_nvm_node_dirs[-1]}/bin" $path)
  fi
  unset _nvm_default _nvm_node_dirs
fi
