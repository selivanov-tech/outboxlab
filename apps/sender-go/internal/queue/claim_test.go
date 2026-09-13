package queue

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestClaimStatementIsTheSharedContractByteForByte(t *testing.T) {
	shared, err := os.ReadFile(filepath.Join("..", "..", "..", "..", "contracts", "jobs", "send_job", "claim.sql"))
	if err != nil {
		t.Fatalf("read shared claim statement: %v", err)
	}
	if string(shared) != ClaimStatement {
		t.Fatalf("ClaimStatement differs from contracts/jobs/send_job/claim.sql")
	}
}

func TestPgxStatementOnlyRenamesTheNamedParameters(t *testing.T) {
	if namedParameter.MatchString(pgxClaimStatement) {
		t.Fatalf("a :name parameter is left in the pgx statement:\n%s", pgxClaimStatement)
	}
	for _, name := range []string{"@moment", "@worker_id", "@workspace_id", "@lease_expired_before", "@limit"} {
		if !strings.Contains(pgxClaimStatement, name) {
			t.Errorf("pgx statement is missing %s", name)
		}
	}
	if strings.ReplaceAll(pgxClaimStatement, "@", ":") != ClaimStatement {
		t.Error("the rewrite changed more than the parameter prefix")
	}
}

func TestFormatUUID(t *testing.T) {
	value := [16]byte{0x01, 0x9e, 0x5f, 0x2a, 0x1a, 0x6d, 0x7f, 0xa2, 0x8b, 0xee, 0x55, 0xd3, 0xe1, 0xcc, 0xdc, 0x3d}
	if got := formatUUID(value); got != "019e5f2a-1a6d-7fa2-8bee-55d3e1ccdc3d" {
		t.Errorf("formatUUID = %q", got)
	}
}
