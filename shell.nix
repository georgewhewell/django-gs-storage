with import <nixpkgs> {}; {
 pyEnv = stdenv.mkDerivation {
   name = "py";
   buildInputs = [
    stdenv
    openssl
    python27Packages.pillow
    python27Packages.virtualenv
  ];
  shellHook = ''
    if [ ! -d env ]
    then
      python -m virtualenv env
    fi
    source env/bin/activate
  '';
 };
}
