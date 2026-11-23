for proj in \
  bind9/arvo_63186 \
  cyclonedds/arvo_56515 \
  dav1d/arvo_60432 \
  exiv2/arvo_61675 exiv2/arvo_64151 exiv2/arvo_50901 \
  kamailio/arvo_38050 kamailio/oss-fuzz_447719691 kamailio/oss-fuzz_391975654 \
  libbpf/arvo_40317 libbpf/arvo_40363 \
  libvips/arvo_39481 \
  libwebsockets/arvo_48959
do
  for run in 1 2 3 4 5
  do
    python scripts/run_agent.py "$proj" \
      --mode e2e \
      --agent codex \
      --model-provider litellm \
      --litellm-model-id deepseek \
      --max-attempts 1 \
      --agent-output "./logs/ds-codex/run_${run}/" \
      --no-firewall
  done
done

for proj in \
  libxaac/arvo_61902 libxaac/arvo_62388 libxaac/arvo_61825 \
  libxslt/arvo_57061 libxslt/arvo_57436 \
  mosquitto/arvo_55886 mosquitto/arvo_57002 mosquitto/arvo_55820 \
  net-snmp/arvo_36908 net-snmp/arvo_64315 net-snmp/arvo_52465 \
  ntopng/arvo_65428 ntopng/arvo_61737 ntopng/arvo_61836
do
  for run in 1 2 3 4 5
  do
    python scripts/run_agent.py "$proj" \
      --mode e2e \
      --agent codex \
      --model-provider litellm \
      --litellm-model-id deepseek \
      --max-attempts 1 \
      --agent-output "./logs/ds-codex/run_${run}/" \
      --no-firewall
  done
done

for proj in \
  open62541/arvo_39741 \
  pcapplusplus/arvo_59650 \
  php/oss-fuzz_449549322 php/oss-fuzz_449413955 php/arvo_42894 \
  quickjs/oss-fuzz_410939009 quickjs/oss-fuzz_413552350 \
  sleuthkit/arvo_36025 sleuthkit/arvo_36955 sleuthkit/arvo_46779 \
  upx/oss-fuzz_383187490 upx/arvo_65531 upx/arvo_65765
do
  for run in 1 2 3 4 5
  do
    python scripts/run_agent.py "$proj" \
      --mode e2e \
      --agent codex \
      --model-provider litellm \
      --litellm-model-id deepseek \
      --max-attempts 1 \
      --agent-output "./logs/ds-codex/run_${run}/" \
      --no-firewall
  done
done