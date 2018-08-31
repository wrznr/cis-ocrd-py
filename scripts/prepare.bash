#!/bin/bash

set -e
source bashlib/ocrd_cis.bash

# configs
for model in Fraktur deu-frak foo; do
	cat > "$TMP_DIR/tessconfig-$model.json" <<EOF
{
 "textequiv_level":"word",
 "model":"$model"
}
EOF
done

odir=$1
if [[ -z $odir ]]; then
	odir=.workspace
fi

# download archives and recognize
gturl='http://www.ocr-d.de/sites/all/GTDaten/IndexGT.html'
for ar in $(wget -O /dev/stdout -o /dev/null $gturl | grep '\.zip' | sed -e 's#.*"\(.*\)".*#\1#'); do
	download_ocrd_gt_zip "$ar"
	wsd="$odir/${ar/.zip/}"
	# setup workspace
	rm -rf "$wsd"
	mkdir -p "$wsd"
	ocrd workspace init "$wsd"
	ocrd-cis-prepare-with-gt \
		--working-dir "$wsd" \
		--mets="$wsd/mets.xml" \
		"$TMP_DIR/downloads/$ar"

	for model in Fraktur deu-frak foo; do
		ocrd-tesserocr-recognize \
			--working-dir "$wsd" \
			--mets "$wsd/mets.xml" \
			--parameter "$TMP_DIR/tessconfig-$model.json" \
			--input-file-grp "OCR-D-SEG-CIS" \
		    --output-file-grp "OCR-D-TESS-$model-COR-CIS"
	done
done
