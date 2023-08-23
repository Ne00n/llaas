cat targets.txt | while read dest;
do
  echo "Running $dest"
  ssh $dest <<EOF
su llaas
cd
timeout 5 git pull --ff-only
exit
EOF
done